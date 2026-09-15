"""Runs the two LIST queries off the GUI thread. Passwords stay in memory only."""
from PySide6.QtCore import QThread, Signal
from .discovery import DiscoveryError, list_folders
from .mapping import propose


class DiscoveryWorker(QThread):
    proposed = Signal(object)   # tuple[Proposal, ...]
    failed = Signal(str)

    def __init__(self, source, destination, passwords, parent=None, lister=list_folders):
        super().__init__(parent)
        self._source, self._destination = source, destination
        self._passwords = tuple(passwords)
        self._lister = lister

    def run(self):
        try:
            source = self._lister(self._source, self._passwords[0])
            destination = self._lister(self._destination, self._passwords[1])
        except DiscoveryError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # never let a worker die silently
            self.failed.emit(f"Découverte interrompue : {type(exc).__name__}.")
        else:
            self.proposed.emit(propose(source, destination))
        finally:
            self._passwords = ()
