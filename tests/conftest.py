import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import time
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(autouse=True)
def history_directory(tmp_path, monkeypatch):
    """No test ever writes into the real user history."""
    directory = tmp_path / "historique"
    monkeypatch.setenv("MAILBOX_HISTORY_DIR", str(directory))
    return directory


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def until(app):
    def wait(predicate, seconds=8):
        deadline = time.monotonic() + seconds
        while not predicate() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.005)
        app.processEvents()
        assert predicate(), "Operation did not finish within timeout"
    return wait
