"""Process/GUI contract tests, NOT real IMAP integration tests."""
from pathlib import Path
import sys
import pytest
from PySide6.QtWidgets import QMessageBox
from mailbox_sync.engine import command
from mailbox_sync.models import Account, Mode, Plan
from mailbox_sync.runner import Runner
from mailbox_sync.ui import Window


@pytest.fixture
def fake_engine(tmp_path, monkeypatch):
    script = tmp_path / "fake_engine.py"
    script.write_text('''import os, sys, time
secret = os.environ["IMAPSYNC_PASSWORD1"]
assert secret not in sys.argv
assert os.environ["IMAPSYNC_PASSWORD2"] == "destination-secret"
if "slow" in sys.argv:
    print("ready", flush=True)
    time.sleep(30)
if "fail" in sys.argv:
    print("authentication failed", flush=True)
    sys.exit(161)
b = ("secret=" + secret + "\\n").encode()
cut = 10
sys.stdout.buffer.write(b[:cut]); sys.stdout.buffer.flush()
time.sleep(0.02)
sys.stdout.buffer.write(b[cut:]); sys.stdout.buffer.flush()
print("mode=" + ("preview" if "--dry" in sys.argv else "login" if "--justlogin" in sys.argv else "copy"), flush=True)
''', encoding="utf-8")
    def fixture_command(plan, mode):
        _, args = command(plan, mode)
        return sys.executable, [str(script), *args]
    monkeypatch.setattr("mailbox_sync.runner.command", fixture_command)
    return script


def plan(user="source"):
    return Plan(Account("source.example", user), Account("dest.example", "destination"), sys.executable)


def test_process_success_redaction_and_cleanup(app, until, fake_engine):
    runner = Runner()
    lines, results = [], []
    runner.line.connect(lines.append)
    runner.done.connect(lambda ok, message: results.append((ok, message)))
    runner.start(plan(), Mode.PREVIEW, ("sécret-value", "destination-secret"))
    temp_dir = runner._temp.name
    until(lambda: bool(results))
    assert results[0][0]
    assert "sécret-value" not in "\n".join(lines)
    assert any("[MASQUÉ]" in line for line in lines)
    assert "mode=preview" in lines
    assert not Path(temp_dir).exists()
    assert not runner.process.processEnvironment().contains("IMAPSYNC_PASSWORD1")
    assert not runner.active


def test_failure_not_success(app, until, fake_engine):
    runner = Runner()
    results = []
    runner.done.connect(lambda ok, msg: results.append((ok, msg)))
    runner.start(plan("fail"), Mode.LOGIN, ("secret", "destination-secret"))
    until(lambda: bool(results))
    assert not results[0][0]
    assert "source" in results[0][1]


def test_stop_and_no_concurrent_run(app, until, fake_engine):
    runner = Runner()
    results, lines = [], []
    runner.line.connect(lines.append)
    runner.done.connect(lambda ok, msg: results.append((ok, msg)))
    runner.start(plan("slow"), Mode.COPY, ("secret", "destination-secret"))
    until(lambda: "ready" in lines)
    with pytest.raises(ValueError):
        runner.start(plan(), Mode.LOGIN, ("secret", "destination-secret"))
    runner.stop()
    until(lambda: bool(results))
    assert not results[0][0]
    assert "arrêtée" in results[0][1]
    assert not runner.active


def test_start_failure_cleans_up(app, until, tmp_path, monkeypatch):
    monkeypatch.setattr("mailbox_sync.runner.command", lambda *args: (str(tmp_path / "missing.exe"), []))
    runner = Runner()
    results = []
    runner.done.connect(lambda ok, msg: results.append((ok, msg)))
    runner.start(plan(), Mode.LOGIN, ("secret", "destination-secret"))
    folder = runner._temp.name
    until(lambda: bool(results))
    assert not results[0][0]
    assert not Path(folder).exists()
    assert not runner.active
    assert not runner.process.processEnvironment().contains("IMAPSYNC_PASSWORD1")


def test_large_line_is_discarded_without_exposing_partial_secret(app):
    runner = Runner()
    lines = []
    runner.line.connect(lines.append)
    runner._consume("x" * 65537)
    runner._consume("secret\nnext\n")
    assert lines == ["[Ligne de journal trop longue omise]", "next"]


def fill(window):
    window.source.set_account(plan().source)
    window.destination.set_account(plan().destination)
    window.source.password.setText("sécret-value")
    window.destination.password.setText("destination-secret")
    window.engine.setText(sys.executable)


def test_ui_preview_gate_invalidation_and_copy(app, until, fake_engine, monkeypatch):
    window = Window()
    window.show()
    fill(window)
    assert not window.copy.isEnabled()
    window._run(Mode.LOGIN)
    assert not window.config.isEnabled()
    until(lambda: not window.runner.active)
    assert not window.copy.isEnabled()
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    assert window.copy.isEnabled()
    window.source.password.setText("changed-secret")
    assert not window.copy.isEnabled()
    window.source.password.setText("sécret-value")
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    window._run(Mode.COPY)
    until(lambda: not window.runner.active)
    assert "mode=copy" in window.log.toPlainText()
    assert "sécret-value" not in window.log.toPlainText()
    assert not window.copy.isEnabled()
    window.close()


def test_ui_failed_preview_never_unlocks_copy(app, until, fake_engine):
    window = Window()
    fill(window)
    window.source.user.setText("fail")
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    assert not window.copy.isEnabled()
    window.close()


def test_profile_load_does_not_authorize_an_executable(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from mailbox_sync.profiles import save_profile
    profile = tmp_path / "saved.json"
    save_profile(profile, plan())
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(profile), ""))
    window = Window()
    fill(window)
    window.preview_plan = window._plan()
    window._open()
    assert not window.engine.text()
    assert not window.source.password.text()
    assert not window.destination.password.text()
    assert window.preview_plan is None
    assert not window.copy.isEnabled()
    window.close()


def test_ui_failed_start_restores_controls(app, until, tmp_path, monkeypatch):
    monkeypatch.setattr("mailbox_sync.runner.command", lambda *args: (str(tmp_path / "missing.exe"), []))
    window = Window()
    fill(window)
    window._run(Mode.PREVIEW)
    until(lambda: not window.runner.active)
    assert window.config.isEnabled()
    assert window.preview.isEnabled()
    assert not window.copy.isEnabled()
    window.close()
