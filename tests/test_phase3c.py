"""Phase 3, lot 3c: local history and report export, without secrets."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import sys
import pytest
from PySide6.QtWidgets import QFileDialog, QMessageBox
from mailbox_sync import history
from mailbox_sync.history_view import HistoryView
from mailbox_sync.models import Account, Filters, FolderMapping, Mode, Plan
from mailbox_sync.report import MigrationReport
from mailbox_sync.ui import Window

SECRET = "sécret-value"


def plan(**options):
    return Plan(Account("source.example", "moi@source.example"),
                Account("dest.example", "moi@dest.example"), sys.executable, **options)


def report(mode=Mode.COPY):
    r = MigrationReport(mode=mode, exit_code=0, size_filter=True)
    for line in ["Messages transferred                    : 3", "Messages skipped : 1",
                 "Messages found in host1 not in host2    : 0 messages", "Detected 0 errors",
                 "Total bytes transferred                 : 4096 (4.000 KiB)",
                 "There is no unidentified message on host1."]:
        r.feed(line)
    return r


def entry(mode=Mode.COPY, **options):
    when = datetime(2026, 9, 15, 10, 30, tzinfo=timezone.utc)
    return history.build(plan(**options), report(mode), True, "Opération terminée.", when, when)


def test_entry_has_no_secret_and_keeps_what_the_bilan_shows(history_directory):
    e = entry(folders=(FolderMapping("Envoyés", "Sent Items"),),
              filters=Filters(since="2024-01-01", max_size=4096))
    path = history.save(e, history_directory)
    text = path.read_text(encoding="utf-8")
    assert SECRET not in text and "password" not in text.lower()
    data = json.loads(text)
    assert data["version"] == 1 and data["mode"] == "copy" and data["ok"] is True
    assert data["source"] == {"host": "source.example", "user": "moi@source.example",
                              "port": 993, "security": "SSL"}
    assert data["folders"] == [{"source": "Envoyés", "destination": "Sent Items"}]
    assert data["filters"]["since"] == "2024-01-01" and data["filters"]["max_size"] == 4096
    assert data["counters"]["transferred"] == 3 and data["counters"]["destination_confirmed"] is True
    assert data["counters"]["transferred_bytes"] == 4096
    assert "log" not in data and "journal" not in text.lower()
    assert history.load(history_directory)[0].counters["skipped"] == 1


def test_entries_are_listed_most_recent_first_and_survive_a_corrupt_file(history_directory):
    for minute in (10, 40, 25):
        e = replace(entry(), started=datetime(2026, 9, 15, 10, minute,
                                              tzinfo=timezone.utc).astimezone().isoformat(timespec="seconds"))
        history.save(e, history_directory)
    (history_directory / "20260915-120000-000-copy.json").write_text("{ broken", encoding="utf-8")
    (history_directory / "notes.txt").write_text("ignoré", encoding="utf-8")
    entries = history.load(history_directory)
    assert len(entries) == 3
    # Sorted by file name, which is built from the local-time stamp, not by insertion order.
    assert [e.started[14:16] for e in entries] == ["40", "25", "10"]


def test_same_second_entries_do_not_overwrite_each_other(history_directory):
    e = entry()
    first, second = history.save(e, history_directory), history.save(e, history_directory)
    assert first != second and len(history.load(history_directory)) == 2


def test_pruning_keeps_the_most_recent(history_directory):
    base = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)
    for index in range(7):
        history.save(replace(entry(), started=(base + timedelta(minutes=index)).astimezone()
                             .isoformat(timespec="seconds")), history_directory)
    history.prune(history_directory, keep=5)
    kept = history.load(history_directory)
    assert len(kept) == 5 and kept[0].started[11:16] > kept[-1].started[11:16]


def test_read_rejects_unknown_version_and_oversized_file(history_directory, tmp_path):
    path = history.save(entry(), history_directory)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = 99
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        history.read(path)
    assert history.load(history_directory) == ()
    big = history_directory / "20260915-090000-000-copy.json"
    big.write_text("x" * (history.MAX_BYTES + 1), encoding="utf-8")
    with pytest.raises(ValueError):
        history.read(big)


def test_report_text_is_complete_and_free_of_secrets():
    e = entry(folders=(FolderMapping("Envoyés", "Sent Items"), FolderMapping("Archives", "")),
              filters=Filters(since="2024-01-01", max_size=25 * 1024))
    text = history.report_text(e)
    assert SECRET not in text
    assert "moi@source.example" in text and "dest.example:993" in text
    assert "Envoyés → Sent Items" in text and "Archives → Archives" in text
    assert "depuis le 2024-01-01" in text and "taille ≤ 25 Kio" in text
    assert "Copiés              : 3" in text and "4,0 Kio" in text
    assert "confirmée par imapsync" in text
    assert "aucun mot de passe" in text
    assert "Périmètre : tous les dossiers" in history.report_text(entry())


def test_export_writes_the_same_text(history_directory, tmp_path):
    e = entry()
    target = history.export(e, tmp_path / "rapport.txt")
    assert target.read_text(encoding="utf-8") == history.report_text(e)


def test_delete_one_and_all(history_directory):
    history.save(entry(), history_directory)
    history.save(entry(Mode.PREVIEW), history_directory)
    entries = history.load(history_directory)
    history.delete(entries[0])
    assert len(history.load(history_directory)) == 1
    assert history.delete_all(history_directory) == 1
    assert history.load(history_directory) == ()


def test_directory_honours_the_override(monkeypatch, tmp_path):
    monkeypatch.setenv("MAILBOX_HISTORY_DIR", str(tmp_path / "ailleurs"))
    assert history.data_directory() == tmp_path / "ailleurs"
    monkeypatch.delenv("MAILBOX_HISTORY_DIR")
    assert "historique" in history.data_directory().parts[-1]


def test_view_lists_shows_exports_and_deletes(app, history_directory, tmp_path, monkeypatch):
    history.save(entry(folders=(FolderMapping("Envoyés", "Sent Items"),)), history_directory)
    view = HistoryView(history_directory)
    assert view.list.count() == 1
    assert "Copie · réussi" in view.list.item(0).text()
    assert "Envoyés → Sent Items" in view.detail.toPlainText()
    target = tmp_path / "export.txt"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    view.export_button.click()
    assert "moi@source.example" in target.read_text(encoding="utf-8")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    view.delete_button.click()
    assert view.list.count() == 0 and not view.detail.toPlainText()
    assert not view.export_button.isEnabled()
    view.deleteLater()


def fill(window):
    window.source.set_account(plan().source)
    window.destination.set_account(plan().destination)
    window.source.password.setText(SECRET)
    window.destination.password.setText("destination-secret")
    window.engine.setText(sys.executable)


def test_ui_records_each_run_without_secrets(app, until, history_directory, monkeypatch, tmp_path):
    script = tmp_path / "engine.py"
    script.write_text('''import sys
print("Messages transferred                    : 1")
print("Messages skipped                        : 0")
print("Messages found in host1 not in host2    : 0 messages")
print("Total bytes transferred                 : 2048 (2.000 KiB)")
print("Detected 0 errors")
print("There is no unidentified message on host1.")
''', encoding="utf-8")
    from mailbox_sync.engine import command as real_command
    monkeypatch.setattr("mailbox_sync.runner.command",
                        lambda p, mode: (sys.executable, [str(script), *real_command(p, mode)[1]]))
    window = Window()
    window.history_directory = history_directory
    window.history.directory = history_directory
    fill(window)
    window.folders.load((FolderMapping("INBOX", "Import"),))
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    entries = history.load(history_directory)
    assert len(entries) == 1 and entries[0].mode == "preview" and entries[0].ok
    assert entries[0].folders == [{"source": "INBOX", "destination": "Import"}]
    assert SECRET not in (history_directory / entries[0].path.name).read_text(encoding="utf-8")
    assert window.history.list.count() == 1
    window.close()


def test_ui_reuse_restores_scope_but_no_account_or_secret(app, history_directory, monkeypatch):
    history.save(entry(folders=(FolderMapping("Envoyés", "Sent Items"),),
                       filters=Filters(since="2024-01-01", max_size=25 * 1024)), history_directory)
    window = Window()
    window.history.directory = history_directory
    window.history.refresh()
    window.preview_plan = window._plan()
    window.copy.setEnabled(True)
    window.history.reuse_button.click()
    assert window.folders.value() == (FolderMapping("Envoyés", "Sent Items"),)
    assert window.filters.value() == Filters(since="2024-01-01", max_size=25 * 1024)
    assert not window.source.password.text() and not window.destination.password.text()
    assert window.preview_plan is None and not window.copy.isEnabled()
    assert "Ressaisis" in window.status.text() or "ressaisis" in window.status.text()
    window.close()


def test_ui_history_failure_is_reported_not_fatal(app, until, monkeypatch, tmp_path):
    monkeypatch.setattr("mailbox_sync.runner.command", lambda *a: (str(tmp_path / "missing.exe"), []))
    monkeypatch.setattr(history, "save", lambda *a, **k: (_ for _ in ()).throw(OSError("disque plein")))
    window = Window()
    fill(window)
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    assert "historique" in window.log.toPlainText()
    assert window.preview.isEnabled()
    window.close()
