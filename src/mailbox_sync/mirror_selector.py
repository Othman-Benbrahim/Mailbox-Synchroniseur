"""Miroir : seule fonction de ce produit capable de supprimer des messages.

Rien n'est mémorisé : la case est décochée à chaque ouverture de l'application et
n'est jamais écrite dans un profil. Elle ne supprime rien à la source, jamais.
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QGroupBox


class MirrorSelector(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        warning = QLabel(
            "Le miroir supprime à destination les messages qui ne sont plus à la source, "
            "pour que la destination reflète exactement la source. C'est la seule fonction "
            "de cette application qui supprime des messages. Elle ne touche jamais la boîte "
            "source. Désactivée à chaque démarrage, jamais enregistrée dans un profil.")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        box = QGroupBox("Suppression à destination")
        inner = QVBoxLayout(box)
        self.enabled = QCheckBox("Activer le miroir : supprimer à destination ce qui n'est plus à la source")
        self.expunge = QCheckBox("Vider définitivement au lieu de marquer « supprimé » (irréversible)")
        self.expunge.setEnabled(False)
        inner.addWidget(self.enabled)
        inner.addWidget(self.expunge)
        detail = QLabel(
            "Par défaut, les messages sont seulement marqués « supprimé » à destination : "
            "ils restent récupérables tant que tu ne vides pas la boîte depuis ton logiciel "
            "de messagerie. Le vidage définitif est une option distincte et irréversible.\n"
            "Une simulation réussie avec le miroir déjà activé est exigée, puis un aperçu "
            "chiffré des suppressions et une confirmation à saisir. Les filtres de dates ou "
            "de taille sont incompatibles avec le miroir : les messages exclus par un filtre "
            "seraient vus comme absents de la source et supprimés à destination.")
        detail.setWordWrap(True)
        detail.setObjectName("muted")
        inner.addWidget(detail)
        layout.addWidget(box)
        layout.addStretch()
        self.enabled.toggled.connect(self._toggle)
        self.expunge.toggled.connect(self.changed)

    def _toggle(self, enabled):
        self.expunge.setEnabled(enabled)
        if not enabled:
            self.expunge.setChecked(False)
        self.changed.emit()

    def value(self):
        return self.enabled.isChecked(), self.enabled.isChecked() and self.expunge.isChecked()

    def reset(self):
        self.expunge.setChecked(False)
        self.enabled.setChecked(False)
