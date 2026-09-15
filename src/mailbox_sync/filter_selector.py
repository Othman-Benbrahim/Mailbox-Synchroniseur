"""Optional date and size filters. Disabled controls mean no filter at all."""
from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel, QCheckBox,
                               QDateEdit, QSpinBox, QGroupBox)
from .models import Filters

KIB = 1024


class FilterSelector(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        hint = QLabel("Les filtres restreignent la sélection dans le périmètre choisi. Les dates sont "
                      "appliquées par le serveur sur la date interne IMAP de chaque message (date de "
                      "réception ou d'archivage), pas sur l'en-tête « Date ». Les tailles portent sur "
                      "le message brut complet, pièces jointes incluses.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        dates = QGroupBox("Dates")
        dates_layout = QFormLayout(dates)
        self.since_enabled = QCheckBox("Ignorer les messages antérieurs au")
        self.since = QDateEdit(QDate.currentDate().addYears(-1))
        self.until_enabled = QCheckBox("Ignorer les messages postérieurs au")
        self.until = QDateEdit(QDate.currentDate())
        for field in (self.since, self.until):
            field.setCalendarPopup(True)
            field.setDisplayFormat("yyyy-MM-dd")
            field.setDateRange(QDate(1970, 1, 1), QDate(2099, 12, 31))
        dates_layout.addRow(self.since_enabled, self.since)
        dates_layout.addRow(self.until_enabled, self.until)
        layout.addWidget(dates)
        sizes = QGroupBox("Tailles (Kio, pièces jointes incluses)")
        sizes_layout = QFormLayout(sizes)
        self.max_enabled = QCheckBox("Ignorer les messages plus grands que")
        self.max_size = QSpinBox()
        self.min_enabled = QCheckBox("Ignorer les messages de taille inférieure ou égale à")
        self.min_size = QSpinBox()
        for field, default in ((self.max_size, 25 * KIB), (self.min_size, 1)):
            field.setRange(1, 1024 * 1024)
            field.setValue(default)
            field.setSuffix(" Kio")
        sizes_layout.addRow(self.max_enabled, self.max_size)
        sizes_layout.addRow(self.min_enabled, self.min_size)
        layout.addWidget(sizes)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addStretch()
        for box, field in ((self.since_enabled, self.since), (self.until_enabled, self.until),
                           (self.max_enabled, self.max_size), (self.min_enabled, self.min_size)):
            field.setEnabled(False)
            box.toggled.connect(field.setEnabled)
            box.toggled.connect(self._changed)
        self.since.dateChanged.connect(self._changed)
        self.until.dateChanged.connect(self._changed)
        self.max_size.valueChanged.connect(self._changed)
        self.min_size.valueChanged.connect(self._changed)
        self._changed()

    def _changed(self):
        self.summary.setText("Filtres actifs : " + self.value().describe())
        self.changed.emit()

    def value(self):
        return Filters(
            self.since.date().toString("yyyy-MM-dd") if self.since_enabled.isChecked() else None,
            self.until.date().toString("yyyy-MM-dd") if self.until_enabled.isChecked() else None,
            self.max_size.value() * KIB if self.max_enabled.isChecked() else None,
            self.min_size.value() * KIB if self.min_enabled.isChecked() else None,
        )

    def load(self, filters):
        # Profiles store bytes; the interface edits whole KiB. Round up so that a
        # loaded filter never becomes more restrictive than the saved one for max_size.
        for box, field, value, rounding in (
                (self.since_enabled, self.since, filters.since, None),
                (self.until_enabled, self.until, filters.until, None),
                (self.max_enabled, self.max_size, filters.max_size, "up"),
                (self.min_enabled, self.min_size, filters.min_size, "down")):
            if value is None:
                box.setChecked(False)
                continue
            if rounding is None:
                field.setDate(QDate.fromString(value, "yyyy-MM-dd"))
            else:
                kib = -(-value // KIB) if rounding == "up" else value // KIB
                field.setValue(max(1, kib))
            box.setChecked(True)
        self._changed()
