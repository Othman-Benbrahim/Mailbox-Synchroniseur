"""Phase 3, lot 3a: date/size filters and volume estimate. Contract tests, not real IMAP."""
from dataclasses import replace
import json
import sys
import pytest
from mailbox_sync.engine import command, search_criteria
from mailbox_sync.filter_selector import FilterSelector
from mailbox_sync.models import Account, Filters, FolderMapping, Mode, Plan
from mailbox_sync.profiles import load_profile, save_profile
from mailbox_sync.report import MigrationReport, human_size
from mailbox_sync.ui import Window


def base(**options):
    return Plan(Account("source.example", "one"), Account("dest.example", "two"), sys.executable, **options)


def test_no_filter_adds_nothing():
    _, args = command(base(), Mode.COPY)
    assert not {"--search", "--maxsize", "--minsize"} & set(args)
    assert not Filters().active
    assert Filters().describe() == "aucun filtre"


@pytest.mark.parametrize("filters,criteria", [
    (Filters(since="2024-01-01"), "SINCE 1-Jan-2024"),
    (Filters(until="2024-12-31"), "BEFORE 1-Jan-2025"),
    (Filters("2024-02-29", "2024-02-29"), "SINCE 29-Feb-2024 BEFORE 1-Mar-2024"),
    (Filters(max_size=1), None),
])
def test_search_criteria_use_rfc3501_english_months_and_inclusive_end(filters, criteria):
    assert search_criteria(filters) == criteria


@pytest.mark.parametrize("mode", [Mode.PREVIEW, Mode.COPY])
def test_filters_in_command(mode):
    p = base(filters=Filters("2024-01-01", "2024-06-30", 25 * 1024, 512),
             folders=(FolderMapping("INBOX", "Import"),))
    _, args = command(p, mode)
    assert args[args.index("--search") + 1] == "SINCE 1-Jan-2024 BEFORE 1-Jul-2024"
    assert args[args.index("--maxsize") + 1] == "25600"
    assert args[args.index("--minsize") + 1] == "512"
    assert "--folder" in args
    assert not {"--delete1", "--delete2", "--expunge"} & set(args)


def test_filters_never_in_login():
    p = base(filters=Filters("2024-01-01", None, 1024, None))
    _, args = command(p, Mode.LOGIN)
    assert not {"--search", "--maxsize", "--minsize"} & set(args)


@pytest.mark.parametrize("filters", [
    Filters(since="2024-13-01"), Filters(since="1-Jan-2024"), Filters(since="2024-1-1"),
    Filters(until="2024-02-30"), Filters("2024-06-01", "2024-05-31"), Filters(since="2024-01-01 OR"),
    Filters(max_size=0), Filters(max_size=-1), Filters(max_size=True), Filters(max_size="1024"),
    Filters(max_size=1024, min_size=1024), Filters(max_size=2 ** 41), Filters(since=20240101),
])
def test_invalid_filters_rejected(filters):
    with pytest.raises(ValueError):
        base(filters=filters).validate()


def test_plan_requires_filters_instance():
    with pytest.raises(ValueError):
        base(filters={"since": "2024-01-01"}).validate()


def test_profiles_v3_v2_and_v1(tmp_path):
    p = base(folders=(FolderMapping("A", "B"),), filters=Filters("2024-01-01", None, 2048, None))
    path = tmp_path / "profile.json"
    save_profile(path, p)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 3
    assert data["filters"] == {"since": "2024-01-01", "until": None, "max_size": 2048, "min_size": None}
    assert "password" not in path.read_text(encoding="utf-8")
    assert load_profile(path) == p
    data.pop("filters")
    data["version"] = 2
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_profile(path) == replace(p, filters=Filters())
    data.pop("folders")
    data["version"] = 1
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_profile(path) == base()


@pytest.mark.parametrize("filters", ['null', '[]', '{"since": "2024-01-01", "extra": 1}',
                                     '{"since": "bad"}', '{"max_size": "1024"}'])
def test_corrupt_v3_filters_rejected(tmp_path, filters):
    path = tmp_path / "profile.json"
    save_profile(path, base())
    data = json.loads(path.read_text(encoding="utf-8"))
    data["filters"] = json.loads(filters)
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_profile(path)


def test_v2_profile_with_filters_key_rejected(tmp_path):
    path = tmp_path / "profile.json"
    save_profile(path, base())
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = 2
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_profile(path)


PREVIEW_OUTPUT = [
    "Host1 Total size:                 50000 bytes (48.828 KiB)",
    "Host2 Total size:                     0 bytes (0.000 KiB)",
    "Messages transferred                    : 0 \t(could be 3 without --dry mode)",
    "Messages skipped                        : 2",
    "Messages found in host1 not in host2    : 3 messages",
    "Total bytes transferred                 : 0 (0.000 KiB)",
    "Total bytes skipped                     : 20000 (19.531 KiB)",
    "Detected 0 errors",
    "There is no unidentified message on host1.",
]


def fed(mode=Mode.PREVIEW, lines=PREVIEW_OUTPUT, **fields):
    r = MigrationReport(mode=mode, exit_code=0, **fields)
    for line in lines:
        r.feed(line)
    return r


def test_preview_report_reads_plannable_and_estimates_by_difference():
    r = fed()
    assert (r.transferred, r.plannable, r.skipped) == (0, 3, 2)
    assert (r.source_bytes, r.skipped_bytes, r.transferred_bytes) == (50000, 20000, 0)
    assert r.estimated_bytes == 30000
    text = r.text()
    assert "À copier : 3" in text and "29,3 Kio" in text and "non communiqué" not in text
    assert not r.destination_confirmed


@pytest.mark.parametrize("change", [{"exit_code": 12}, {"errors": 1}, {"errors": None},
                                   {"source_bytes": None}, {"skipped_bytes": None},
                                   {"skipped_bytes": 60000}, {"mode": Mode.COPY}])
def test_estimate_requires_evidence(change):
    assert replace(fed(), **change).estimated_bytes is None


def test_absent_counters_are_reported_as_unknown():
    r = MigrationReport(mode=Mode.PREVIEW, exit_code=0)
    assert r.plannable is None and r.estimated_bytes is None
    assert r.text().count("non communiqué") == 7


def test_copy_report_shows_transferred_volume_and_ignores_could_be():
    lines = [line.replace(" \t(could be 3 without --dry mode)", "") for line in PREVIEW_OUTPUT]
    lines = [line.replace("Total bytes transferred                 : 0", "Total bytes transferred                 : 30000")
             .replace("Messages transferred                    : 0", "Messages transferred                    : 3")
             .replace("host1 not in host2    : 3", "host1 not in host2    : 0") for line in lines]
    r = fed(Mode.COPY, lines)
    assert r.plannable is None and r.transferred == 3 and r.transferred_bytes == 30000
    assert r.destination_confirmed and "29,3 Kio" in r.text() and "confirmée par imapsync" in r.text()


def test_password_digits_do_not_corrupt_counters():
    r = fed(lines=["Total bytes skipped                     : 20000 (19.531 KiB) 12345"])
    assert r.skipped_bytes == 20000


@pytest.mark.parametrize("value,text", [(0, "0 octets"), (1023, "1023 octets"), (1024, "1,0 Kio"),
                                        (1536, "1,5 Kio"), (5 * 1024 ** 2, "5,0 Mio"), (3 * 1024 ** 4, "3,0 Tio")])
def test_human_size(value, text):
    assert human_size(value) == text


def test_filter_selector_roundtrip_and_kib_rounding(app):
    widget = FilterSelector()
    assert widget.value() == Filters()
    widget.load(Filters("2024-01-01", "2024-12-31", 25 * 1024, 2 * 1024))
    assert widget.value() == Filters("2024-01-01", "2024-12-31", 25 * 1024, 2 * 1024)
    assert "du 2024-01-01 au 2024-12-31" in widget.summary.text()
    widget.load(Filters(max_size=1025, min_size=2047))
    # max rounds up, min rounds down: the loaded filter is never more restrictive.
    assert widget.value() == Filters(max_size=2 * 1024, min_size=1 * 1024)
    widget.load(Filters())
    assert widget.value() == Filters()
    assert not widget.since.isEnabled() and not widget.max_size.isEnabled()


def test_filter_change_invalidates_preview_and_shows_in_scope(app):
    window = Window()
    window.preview_plan = window._plan()
    window.copy.setEnabled(True)
    window.filters.max_enabled.setChecked(True)
    assert window.preview_plan is None
    assert not window.copy.isEnabled()
    assert "taille ≤ 25600 Kio" in window.scope.text()
    assert window._plan().filters == Filters(max_size=25600 * 1024)
    window.preview_plan = window._plan()
    window.copy.setEnabled(True)
    window.filters.max_size.setValue(10)
    assert window.preview_plan is None and not window.copy.isEnabled()
    window.close()


def test_swap_keeps_filters(app):
    window = Window()
    window.filters.load(Filters(since="2024-01-01"))
    window._swap()
    assert window._plan().filters == Filters(since="2024-01-01")
    window.close()


def test_size_filtered_messages_explain_missing_but_nothing_else():
    lines = ["msg INBOX/7 skipped (30000 exceeds maxsize limit 4096 bytes)",
             "msg Archives/Été & 日本語/2 skipped (10 smaller than minsize 512 bytes)",
             "Messages found in host1 not in host2    : 2 messages", "Detected 0 errors",
             "There is no unidentified message on host1."]
    r = fed(Mode.COPY, lines, size_filter=True)
    assert r.size_filtered == 2 and r.missing == 2 and r.unexplained_missing == 0
    assert r.destination_confirmed
    assert "dont 2 exclus par le filtre de taille" in r.text() and "hors messages exclus" in r.text()
    assert not replace(r, missing=3).destination_confirmed
    assert replace(r, missing=3).unexplained_missing == 1
    assert not replace(r, missing=1).destination_confirmed
    assert MigrationReport(mode=Mode.COPY).unexplained_missing is None


@pytest.mark.parametrize("ending", ["\n", "\r\n", ""])
def test_counters_are_read_with_any_line_ending(ending):
    """Windows engines and QProcess deliver CRLF; the CI on windows-latest caught this."""
    lines = [line + ending for line in PREVIEW_OUTPUT +
             ["msg INBOX/7 skipped (30000 exceeds maxsize limit 4096 bytes)"]]
    r = fed(lines=lines)
    assert (r.plannable, r.skipped, r.source_bytes, r.skipped_bytes, r.unidentified, r.errors) == (3, 2, 50000, 20000, 0, 0)
    assert r.size_filtered == 1


def test_preview_with_size_filter_states_the_limit():
    text = fed(size_filter=True).text()
    assert "avant filtre de taille" in text
    assert "avant filtre de taille" not in fed().text()


def test_runner_copy_with_size_filter_is_not_a_failure(app, until, tmp_path, monkeypatch):
    script = tmp_path / "engine.py"
    # Written with explicit CRLF: this is what the engine produces on Windows.
    script.write_text('''import sys
out = sys.stdout.buffer
for line in ("msg INBOX/7 skipped (30000 exceeds maxsize limit 4096 bytes)",
             "Messages transferred                    : 1",
             "Messages found in host1 not in host2    : 1 messages",
             "Total bytes transferred                 : 2000 (1.953 KiB)",
             "Detected 0 errors",
             "There is no unidentified message on host1."):
    out.write((line + "\\r\\n").encode())
out.flush()
''', encoding="utf-8")
    monkeypatch.setattr("mailbox_sync.runner.command", lambda plan, mode: (sys.executable, [str(script)]))
    from mailbox_sync.runner import Runner
    runner = Runner()
    results = []
    runner.done.connect(lambda ok, msg: results.append((ok, msg)))
    runner.start(base(filters=Filters(max_size=4096)), Mode.COPY, ("a", "b"))
    until(lambda: bool(results))
    assert results[0][0], results
    assert runner.report.size_filter and runner.report.destination_confirmed
    runner = Runner()
    results = []
    runner.done.connect(lambda ok, msg: results.append((ok, msg)))
    runner.start(base(), Mode.COPY, ("a", "b"))
    until(lambda: bool(results))
    # Same output without a size filter in the plan: the skipped line is still the
    # engine's evidence, so the outcome is identical; the flag only shapes the text.
    assert results[0][0], results
