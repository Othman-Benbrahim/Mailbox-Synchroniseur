"""Phase 6, packaging: the application must find the engine shipped beside it.

The build chain itself (PyInstaller, PAR::Packer, Inno Setup) is exercised by the
Windows workflow, not here. What is testable everywhere is the contract between
the packaged layout and the application.
"""
import os
import sys
import pytest
from mailbox_sync import __version__
from mailbox_sync.bundle import application_directory, bundled_engine, is_frozen
from mailbox_sync.ui import Window


def make_engine(directory, name="imapsync"):
    folder = directory / "engine"
    folder.mkdir(parents=True, exist_ok=True)
    engine = folder / name
    engine.write_text("#!/bin/sh\necho 2.314\n", encoding="utf-8")
    engine.chmod(0o755)
    return engine


def test_no_engine_folder_means_no_bundled_engine(tmp_path):
    assert bundled_engine(tmp_path) is None
    (tmp_path / "engine").mkdir()
    assert bundled_engine(tmp_path) is None


def test_an_engine_beside_the_application_is_found(tmp_path):
    engine = make_engine(tmp_path)
    assert bundled_engine(tmp_path) == engine


@pytest.mark.skipif(os.name == "nt", reason="Windows n'utilise pas le bit exécutable")
def test_a_non_executable_file_is_not_taken_for_an_engine(tmp_path):
    engine = make_engine(tmp_path)
    engine.chmod(0o644)
    assert bundled_engine(tmp_path) is None


def test_a_directory_named_like_the_engine_is_ignored(tmp_path):
    (tmp_path / "engine" / "imapsync").mkdir(parents=True)
    assert bundled_engine(tmp_path) is None


def test_the_windows_name_is_accepted(tmp_path):
    engine = make_engine(tmp_path, "imapsync.exe")
    assert bundled_engine(tmp_path) == engine


def test_running_from_sources_is_not_frozen_and_points_at_the_project():
    assert not is_frozen()
    assert (application_directory() / "src" / "mailbox_sync").is_dir()


def test_frozen_application_looks_next_to_the_executable(tmp_path, monkeypatch):
    executable = tmp_path / "Mailbox-Synchroniseur.exe"
    executable.write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    assert application_directory() == tmp_path
    engine = make_engine(tmp_path)
    assert bundled_engine() == engine


def test_the_interface_preselects_a_bundled_engine(app, tmp_path, monkeypatch):
    engine = make_engine(tmp_path)
    monkeypatch.setattr("mailbox_sync.ui.bundled_engine", lambda: engine)
    window = Window()
    assert window.engine.text() == str(engine)
    assert window._plan().engine == str(engine)
    window.close()


def test_without_a_bundled_engine_the_field_is_not_invented(app, monkeypatch):
    monkeypatch.setattr("mailbox_sync.ui.bundled_engine", lambda: None)
    monkeypatch.setattr("mailbox_sync.ui.shutil.which", lambda name: None)
    window = Window()
    assert window.engine.text() == ""
    window.close()


def test_a_bundled_engine_stays_replaceable(app, tmp_path, monkeypatch):
    """A shipped engine is a default, never a constraint."""
    monkeypatch.setattr("mailbox_sync.ui.bundled_engine", lambda: make_engine(tmp_path))
    window = Window()
    assert window.engine.isEnabled() and not window.engine.isReadOnly()
    window.engine.setText(sys.executable)
    assert window._plan().engine == sys.executable
    window.close()


def test_version_flag_prints_one_stable_line(capsys):
    from mailbox_sync.__main__ import main
    monkey = sys.argv
    sys.argv = ["mailbox-synchroniseur", "--version"]
    try:
        assert main() == 0
    finally:
        sys.argv = monkey
    printed = capsys.readouterr().out.strip()
    # The Windows workflow compares this line to the package version.
    assert printed == f"Mailbox Synchroniseur {__version__}"
    assert "\n" not in printed
