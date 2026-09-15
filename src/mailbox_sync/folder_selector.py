from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
                              QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
                              QPlainTextEdit)
from .mapping import describe
from .models import FolderMapping


class FolderSelector(QWidget):
    changed = Signal()
    discover_requested = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.enabled = QCheckBox("Copier uniquement les dossiers ci-dessous")
        layout.addWidget(self.enabled)
        hint = QLabel("Saisis les noms complets des dossiers source, par exemple INBOX ou Archives/2025.\n"
                      "Une destination vide conserve le même nom. Ajoute chaque sous-dossier séparément.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Dossier source (nom exact)", "Dossier destination"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(180)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        self.add_button = QPushButton("Ajouter un dossier")
        self.remove_button = QPushButton("Retirer la ligne")
        self.discover_button = QPushButton("Découvrir et proposer…")
        self.discover_button.setToolTip("Liste les dossiers des deux comptes (lecture seule) et remplit "
                                        "le tableau avec une proposition à vérifier.")
        row.addWidget(self.add_button)
        row.addWidget(self.remove_button)
        row.addWidget(self.discover_button)
        row.addStretch()
        layout.addLayout(row)
        self.explanations = QPlainTextEdit()
        self.explanations.setObjectName("log")
        self.explanations.setReadOnly(True)
        self.explanations.setMaximumHeight(140)
        self.explanations.setPlaceholderText("La proposition de correspondance et ses raisons apparaîtront ici. "
                                             "Le tableau reste modifiable ; une simulation reste obligatoire.")
        layout.addWidget(self.explanations)
        self.enabled.toggled.connect(self._toggle)
        self.table.cellChanged.connect(self.changed)
        self.add_button.clicked.connect(self.add)
        self.remove_button.clicked.connect(self.remove)
        self.discover_button.clicked.connect(self.discover_requested)
        self._toggle(False)

    def _toggle(self, enabled):
        for widget in (self.table, self.add_button, self.remove_button):
            widget.setEnabled(enabled)
        self.changed.emit()

    def add(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(2):
            self.table.setItem(row, col, QTableWidgetItem(""))
        self.table.setCurrentCell(row, 0)
        self.changed.emit()

    def remove(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self.changed.emit()

    def value(self):
        if not self.enabled.isChecked():
            return None
        return tuple(FolderMapping(self.table.item(row, 0).text(), self.table.item(row, 1).text())
                     for row in range(self.table.rowCount()))

    def load(self, folders):
        self.table.setRowCount(0)
        for mapping in folders or ():
            self.add()
            row = self.table.rowCount() - 1
            self.table.item(row, 0).setText(mapping.source)
            self.table.item(row, 1).setText(mapping.destination)
        self.enabled.setChecked(folders is not None)
        self.changed.emit()

    def invert(self):
        folders = self.value()
        if folders is not None:
            self.load(tuple(FolderMapping(f.destination or f.source, f.source) for f in folders))
        self.explanations.clear()

    def apply_proposal(self, proposals):
        """Fill the table with the proposal; excluded folders are listed, not added."""
        mappings = tuple(p.mapping for p in proposals if p.mapping is not None)
        self.explanations.setPlainText(describe(proposals))
        if mappings:
            self.load(mappings)
        else:
            self.load(None)
