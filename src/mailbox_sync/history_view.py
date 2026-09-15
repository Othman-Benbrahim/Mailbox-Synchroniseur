"""Historique local : liste des opérations, détail, export, suppression."""
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QPushButton, QMessageBox,
                               QFileDialog, QSplitter)
from PySide6.QtCore import Qt
from . import history


class HistoryView(QWidget):
    reuse_requested = Signal(object)   # history.Entry

    def __init__(self, directory=None):
        super().__init__()
        self.directory = directory
        layout = QVBoxLayout(self)
        hint = QLabel("Les opérations terminées sont enregistrées localement, sans mot de passe "
                      "et sans le journal. Chaque entrée est un fichier JSON que tu peux relire "
                      "ou supprimer. Les 200 plus récentes sont conservées.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setMinimumWidth(320)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText("Sélectionne une opération pour afficher son rapport.")
        splitter.addWidget(self.list)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        row = QHBoxLayout()
        self.refresh_button = QPushButton("Actualiser")
        self.export_button = QPushButton("Exporter le rapport…")
        self.reuse_button = QPushButton("Reprendre ce périmètre")
        self.delete_button = QPushButton("Supprimer l'entrée")
        self.clear_button = QPushButton("Tout supprimer")
        for button in (self.refresh_button, self.export_button, self.reuse_button,
                       self.delete_button, self.clear_button):
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        self.location = QLabel()
        self.location.setWordWrap(True)
        self.location.setObjectName("muted")
        layout.addWidget(self.location)
        self.list.currentItemChanged.connect(self._show)
        self.refresh_button.clicked.connect(self.refresh)
        self.export_button.clicked.connect(self._export)
        self.reuse_button.clicked.connect(self._reuse)
        self.delete_button.clicked.connect(self._delete)
        self.clear_button.clicked.connect(self._clear)
        self.refresh()

    def entries(self):
        return tuple(self.list.item(row).data(Qt.ItemDataRole.UserRole)
                     for row in range(self.list.count()))

    def current(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def refresh(self):
        self.list.clear()
        for entry in history.load(self.directory):
            item = QListWidgetItem(entry.label)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.list.addItem(item)
        empty = self.list.count() == 0
        for button in (self.export_button, self.reuse_button, self.delete_button):
            button.setEnabled(not empty)
        self.clear_button.setEnabled(not empty)
        if empty:
            self.detail.clear()
        else:
            self.list.setCurrentRow(0)
        directory = Path(self.directory or history.data_directory())
        self.location.setText(f"Dossier de l'historique : {directory}")

    def _show(self, item, _previous=None):
        entry = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.detail.setPlainText(history.report_text(entry) if entry else "")

    def _export(self):
        entry = self.current()
        if entry is None:
            return
        suggestion = f"rapport-{entry.started[:19].replace(':', '-')}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Exporter le rapport (sans mots de passe)",
                                              suggestion, "Texte (*.txt)")
        if path:
            try:
                history.export(entry, Path(path))
            except OSError as exc:
                QMessageBox.warning(self, "Export impossible", str(exc))

    def _reuse(self):
        entry = self.current()
        if entry is not None:
            self.reuse_requested.emit(entry)

    def _delete(self):
        entry = self.current()
        if entry is None:
            return
        if QMessageBox.question(self, "Supprimer l'entrée", f"Supprimer « {entry.label} » ?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            history.delete(entry)
            self.refresh()

    def _clear(self):
        if QMessageBox.question(self, "Tout supprimer", "Supprimer toutes les entrées de l'historique ?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            history.delete_all(self.directory)
            self.refresh()
