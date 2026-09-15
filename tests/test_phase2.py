from dataclasses import replace
import json
import sys
import pytest
from mailbox_sync.engine import command
from mailbox_sync.folders import imap_utf7
from mailbox_sync.models import Account, FolderMapping, Mode, Plan
from mailbox_sync.profiles import load_profile, save_profile
from mailbox_sync.report import MigrationReport
from mailbox_sync.ui import Window


def base():
    return Plan(Account("source.example", "one"), Account("dest.example", "two"), sys.executable)


@pytest.mark.parametrize("text,encoded", [("INBOX", "INBOX"), ("A&B", "A&-B"),
                                         ("Été", "&AMk-t&AOk-"), ("日本語", "&ZeVnLIqe-")])
def test_imap_utf7(text, encoded):
    assert imap_utf7(text) == encoded


def test_selected_command():
    p = replace(base(), folders=(FolderMapping("Archives/Été", "Import/Été"),))
    _, args = command(p, Mode.PREVIEW)
    assert args[args.index("--folder")+1] == "Archives/&AMk-t&AOk-"
    assert args[args.index("--f1f2")+1] == "Archives/&AMk-t&AOk-=Import/&AMk-t&AOk-"
    assert "--dry" in args
    assert "--folder" not in command(p, Mode.LOGIN)[1]


@pytest.mark.parametrize("folders", [(), (FolderMapping("", "x"),), (FolderMapping("a=b", "x"),),
    (FolderMapping("a", "x"), FolderMapping("b", "X")),
    (FolderMapping("a", "x"), FolderMapping("A", "y")), (FolderMapping("--delete1", "x"),)])
def test_invalid_selections(folders):
    with pytest.raises(ValueError):
        replace(base(), folders=folders).validate()


def test_profiles_v2_and_legacy(tmp_path):
    p = replace(base(), folders=(FolderMapping("A", "B"),))
    path = tmp_path / "profile.json"
    save_profile(path, p)
    assert load_profile(path) == p
    data = json.loads(path.read_text())
    data.pop("folders")
    data.pop("filters")
    data["version"] = 1
    path.write_text(json.dumps(data))
    assert load_profile(path) == base()


def report(mode=Mode.COPY):
    r = MigrationReport(mode=mode, exit_code=0)
    for line in ["Messages transferred : 12", "Messages skipped : 8",
                 "Messages found in host1 not in host2 : 0 messages", "Detected 0 errors",
                 "There is no unidentified message on host1."]:
        r.feed(line)
    return r


def test_report_requires_evidence():
    assert not MigrationReport(mode=Mode.COPY, exit_code=0).destination_confirmed
    assert not report(Mode.PREVIEW).destination_confirmed
    r = report()
    assert r.destination_confirmed and r.transferred == 12 and r.skipped == 8
    r.feed("There are 1 unidentified messages (usually Sent or Draft messages).")
    assert not r.destination_confirmed


@pytest.mark.parametrize("change", [{"exit_code": 113}, {"cancelled": True}, {"crashed": True},
                                   {"missing": 1}, {"errors": 1}, {"errors": None}])
def test_report_rejects_incomplete(change):
    assert not replace(report(), **change).destination_confirmed


def test_folder_change_invalidates_preview_and_inverse(app):
    window = Window()
    window.folders.load((FolderMapping("INBOX", "Imported"),))
    window.preview_plan = window._plan()
    window.copy.setEnabled(True)
    window.folders.table.item(0, 1).setText("Other")
    assert window.preview_plan is None
    assert not window.copy.isEnabled()
    window.folders.invert()
    assert window.folders.value() == (FolderMapping("Other", "INBOX"),)
    window.close()
