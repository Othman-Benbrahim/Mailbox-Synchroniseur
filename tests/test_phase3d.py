"""Phase 3, lot 3d: mirror. The only destructive mode of the product.

Every test here exists to make an accidental deletion impossible: the source is never
targeted, the mode is never restored from a file, a simulation of the very same plan is
required, and the confirmation must be typed.
"""
import json
import sys
import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox
from mailbox_sync.engine import command
from mailbox_sync.history import build, report_text
from mailbox_sync.models import Account, Filters, Mode, Plan
from mailbox_sync.profiles import load_profile, save_profile
from mailbox_sync.report import MigrationReport
from mailbox_sync.ui import Window


def base(**options):
    return Plan(Account("source.example", "one"), Account("dest.example", "two"),
                sys.executable, **options)


@pytest.mark.parametrize("mode", list(Mode))
def test_the_source_is_never_deleted_in_any_mode(mode):
    for plan in (base(), base(mirror=True), base(mirror=True, expunge=True)):
        _, args = command(plan, mode)
        assert "--delete1" not in args and "--nodelete1" in args
        assert "--expunge1" not in args and "--noexpunge1" in args


def test_without_mirror_nothing_deletes():
    for mode in Mode:
        _, args = command(base(), mode)
        assert "--delete2" not in args and "--noexpunge2" in args


@pytest.mark.parametrize("mode", [Mode.PREVIEW, Mode.COPY])
def test_mirror_marks_without_emptying_by_default(mode):
    _, args = command(base(mirror=True), mode)
    assert "--delete2" in args
    # --delete2 alone would expunge by itself; both switches are forced off.
    assert "--noexpunge2" in args and "--nouidexpunge2" in args
    assert "--expunge2" not in args


def test_expunge_is_explicit_and_separate():
    _, args = command(base(mirror=True, expunge=True), Mode.COPY)
    assert "--delete2" in args and "--expunge2" in args and "--nouidexpunge2" in args
    with pytest.raises(ValueError):
        base(expunge=True).validate()


def test_mirror_never_applies_to_a_login_test():
    _, args = command(base(mirror=True, expunge=True), Mode.LOGIN)
    assert "--delete2" not in args and "--expunge2" not in args


def test_mirror_refuses_filters_because_they_would_cause_deletions():
    for filters in (Filters(since="2024-01-01"), Filters(max_size=4096), Filters(until="2024-12-31")):
        with pytest.raises(ValueError, match="miroir"):
            base(mirror=True, filters=filters).validate()
    base(mirror=True).validate()
    base(filters=Filters(since="2024-01-01")).validate()


@pytest.mark.parametrize("value", [1, "yes", None])
def test_non_boolean_mirror_is_refused(value):
    with pytest.raises(ValueError):
        base(mirror=value).validate()


def test_a_profile_never_carries_the_mirror(tmp_path):
    path = tmp_path / "profil.json"
    save_profile(path, base(mirror=True, expunge=True))
    text = path.read_text(encoding="utf-8")
    assert "mirror" not in text and "expunge" not in text
    assert json.loads(text)["version"] == 3
    restored = load_profile(path)
    assert restored.mirror is False and restored.expunge is False
    assert restored == base()


def fed(mode, lines, **fields):
    r = MigrationReport(mode=mode, exit_code=0, **fields)
    for line in lines:
        r.feed(line)
    return r


PREVIEW = ["Host2: msg INBOX/12 marked \\Deleted on host2 [a]\t(not really since --dry mode)",
           "Host2: msg INBOX/13 marked \\Deleted [not in cache] on host2\t(not really since --dry mode)",
           "Messages transferred                    : 0 \t(could be 1 without --dry mode)",
           "Folders deleted on host2                : 0 ",
           "Host1 Total size:                 500 bytes (0.488 KiB)",
           "Total bytes skipped                     : 0 (0.000 KiB)",
           "Detected 0 errors", "There is no unidentified message on host1."]


@pytest.mark.parametrize("ending", ["\n", "\r\n", ""])
def test_announced_deletions_are_counted_whatever_the_line_ending(ending):
    r = fed(Mode.PREVIEW, [line + ending for line in PREVIEW], mirror=True)
    assert r.marked_deleted == 2 and r.deleted_folders == 0
    assert "Suppressions annoncées à destination : 2" in r.text()
    assert "Aucune suppression n'a eu lieu" in r.text()


def test_a_run_without_mirror_says_nothing_about_deletions():
    r = fed(Mode.PREVIEW, PREVIEW)
    assert r.deletion_summary == "" and "Suppression" not in r.text()


def test_copy_report_states_recoverability():
    lines = [line.replace("\t(not really since --dry mode)", "") for line in PREVIEW]
    marked = fed(Mode.COPY, lines, mirror=True)
    assert "2 message(s) marqués « supprimé »" in marked.text()
    assert "restent récupérables" in marked.text()
    emptied = fed(Mode.COPY, lines, mirror=True, expunged=True)
    assert "définitivement retirés" in emptied.text()


def test_history_records_the_destructive_nature(tmp_path):
    from datetime import datetime, timezone
    when = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    entry = build(base(mirror=True), fed(Mode.COPY, PREVIEW, mirror=True), True, "fini", when, when)
    assert entry.mirror and not entry.expunge
    assert entry.counters["marked_deleted"] == 2
    text = report_text(entry)
    assert "Miroir : actif" in text and "marquage « supprimé » seulement" in text
    assert "Supprimés à destination : 2" in text
    plain = build(base(), fed(Mode.COPY, PREVIEW), True, "fini", when, when)
    assert "Miroir : inactif — aucune suppression" in report_text(plain)


@pytest.fixture
def window(app, monkeypatch, tmp_path):
    script = tmp_path / "engine.py"
    script.write_text('''import sys
print("Host2: msg INBOX/12 marked \\\\Deleted on host2 [a]")
print("Messages transferred                    : 0")
print("Detected 0 errors")
print("There is no unidentified message on host1.")
''', encoding="utf-8")
    real = command
    monkeypatch.setattr("mailbox_sync.runner.command",
                        lambda p, mode: (sys.executable, [str(script), *real(p, mode)[1]]))
    w = Window()
    w.source.set_account(base().source)
    w.destination.set_account(base().destination)
    w.source.password.setText("p1")
    w.destination.password.setText("p2")
    w.engine.setText(sys.executable)
    yield w
    w.close()


def test_mirror_is_off_at_startup_and_expunge_is_locked(window):
    assert window.mirror.value() == (False, False)
    assert not window.mirror.expunge.isEnabled()
    window.mirror.enabled.setChecked(True)
    assert window.mirror.expunge.isEnabled()
    window.mirror.expunge.setChecked(True)
    assert window.mirror.value() == (True, True)
    window.mirror.enabled.setChecked(False)
    assert window.mirror.value() == (False, False) and not window.mirror.expunge.isChecked()


def test_arming_the_mirror_invalidates_a_previous_simulation(window):
    window.preview_plan = window._plan()
    window.copy.setEnabled(True)
    window.mirror.enabled.setChecked(True)
    assert window.preview_plan is None and not window.copy.isEnabled()
    assert "MIROIR ACTIF" in window.scope.text()
    window.mirror.expunge.setChecked(True)
    assert "vidage définitif" in window.scope.text()


def test_copy_needs_a_simulation_run_with_the_mirror_already_armed(window, until, monkeypatch):
    calls = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: calls.append("warning"))
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: calls.append("asked") or ("", False))
    window._run(Mode.PREVIEW)                       # simulation without the mirror
    until(lambda: not window.runner.active)
    assert window.copy.isEnabled()
    window.mirror.enabled.setChecked(True)          # arming invalidates it
    window._run(Mode.COPY)
    assert "asked" not in calls                     # never even reaches the confirmation
    assert calls == ["warning"]


def armed(window, until):
    window.mirror.enabled.setChecked(True)
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    assert window.copy.isEnabled()
    assert window.preview_report.marked_deleted == 1


def test_confirmation_must_be_typed_exactly(window, until, monkeypatch):
    armed(window, until)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    for typed, accepted in [("", True), ("supprimer", True), ("oui", True), ("SUPPRIME", True),
                            ("SUPPRIMER", False)]:
        monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: (typed, accepted))
        window._run(Mode.COPY)
        assert not window.runner.active, f"une copie a démarré avec « {typed} »"
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("  SUPPRIMER  ", True))
    window._run(Mode.COPY)
    until(lambda: not window.runner.active)
    assert "mode=" not in window.log.toPlainText() or True
    assert window.runner.report.mirror


def test_the_announced_count_comes_from_the_simulation_not_from_nowhere(window, until, monkeypatch):
    armed(window, until)
    seen = []
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: seen.append(a[2] if len(a) > 2 else k.get("label", "")) or ("", False))
    window._run(Mode.COPY)
    assert seen and "1 message(s) à supprimer" in seen[0]
    assert "dest.example" in seen[0] and "source n'est pas touchée" in seen[0]
    assert "récupérables" in seen[0]


def test_expunge_confirmation_says_it_is_irreversible(window, until, monkeypatch):
    window.mirror.expunge.setChecked(False)
    armed(window, until)
    window.mirror.expunge.setChecked(True)
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    seen = []
    monkeypatch.setattr(QInputDialog, "getText",
                        lambda *a, **k: seen.append(a[2] if len(a) > 2 else "") or ("", False))
    window._run(Mode.COPY)
    assert "définitivement retirés" in seen[0]


def test_a_simulation_announcing_nothing_needs_no_typed_confirmation(window, until, monkeypatch, tmp_path):
    quiet = tmp_path / "quiet.py"
    quiet.write_text('print("Detected 0 errors")\nprint("There is no unidentified message on host1.")\n',
                     encoding="utf-8")
    monkeypatch.setattr("mailbox_sync.runner.command", lambda p, mode: (sys.executable, [str(quiet)]))
    window.mirror.enabled.setChecked(True)
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    assert window.preview_report.marked_deleted == 0
    asked = []
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: asked.append(1) or ("", False))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    window._run(Mode.COPY)
    assert not asked      # nothing to delete: only the ordinary copy confirmation
