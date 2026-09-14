from pathlib import Path
import shutil
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QTabWidget,
)
from . import __version__
from .models import Account, Mode, Plan
from .profiles import load_profile, save_profile
from .runner import Runner
from .folder_selector import FolderSelector

STYLE = """
QWidget { font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 13px; color: #192d42; }
QMainWindow, QScrollArea, #page { background: #f3f6fa; }
QGroupBox { background: white; border: 1px solid #d6dfe9; border-radius: 10px;
            margin-top: 18px; padding: 20px 14px 14px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 6px; }
QLineEdit, QSpinBox, QComboBox { background: white; padding: 8px; border: 1px solid #b8c8d9; border-radius: 5px; }
QLineEdit:focus, QSpinBox:focus { border: 1px solid #14736a; }
QPushButton { padding: 9px 15px; background: white; border: 1px solid #b8c8d9; border-radius: 6px; }
QPushButton:hover { background: #e7f2ef; border-color: #14736a; }
QPushButton:disabled { color: #7b8898; background: #edf0f4; border-color: #d7dfe7; }
QPushButton#primary { background: #146f66; color: white; border: none; font-weight: bold; }
QPushButton#primary:disabled { background: #baccc9; color: #f5f8f7; }
QPlainTextEdit { background: #172738; color: #e3edf5; border: none; border-radius: 7px;
                 font-family: 'Consolas', monospace; font-size: 12px; padding: 10px; }
QProgressBar { border: none; background: #dfe8ef; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #188779; }
QLabel#title { font-size: 27px; font-weight: bold; }
QLabel#muted { color: #52687c; }
"""


class AccountCard(QGroupBox):
    changed = Signal()

    def __init__(self, title):
        super().__init__(title)
        layout = QFormLayout(self)
        self.host = QLineEdit()
        self.host.setPlaceholderText("imap.exemple.fr")
        self.user = QLineEdit()
        self.user.setPlaceholderText("prenom@exemple.fr")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Mot de passe ou mot de passe d'application")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(993)
        self.security = QComboBox()
        self.security.addItem("TLS direct (993)", "SSL")
        self.security.addItem("STARTTLS (143)", "STARTTLS")
        self.security.currentIndexChanged.connect(self._security_changed)
        self.show_password = QCheckBox("Afficher")
        self.show_password.toggled.connect(lambda show: self.password.setEchoMode(
            QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password))
        for label, field in (("Serveur", self.host), ("Identifiant", self.user),
                             ("Mot de passe", self.password), ("Connexion", self.security),
                             ("Port", self.port)):
            layout.addRow(label, field)
        layout.addRow("", self.show_password)
        for field in (self.host, self.user, self.password):
            field.textChanged.connect(self.changed)
        self.port.valueChanged.connect(self.changed)
        self.security.currentIndexChanged.connect(self.changed)

    def _security_changed(self):
        self.port.setValue(993 if self.security.currentData() == "SSL" else 143)

    def account(self):
        return Account(self.host.text().strip(), self.user.text().strip(),
                       self.port.value(), self.security.currentData())

    def set_account(self, account):
        self.host.setText(account.host)
        self.user.setText(account.user)
        self.security.setCurrentIndex(self.security.findData(account.security))
        self.port.setValue(account.port)
        self.password.clear()
        self.show_password.setChecked(False)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Mailbox Synchroniseur — {__version__}")
        self.resize(1060, 840)
        self.setMinimumSize(780, 620)
        self.setStyleSheet(STYLE)
        self.preview_plan = None
        self.current_plan = None
        self.current_mode = None
        self.close_after_run = False
        self.runner = Runner(self)
        self.runner.line.connect(self._line)
        self.runner.done.connect(self._done)
        page = QWidget()
        page.setObjectName("page")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(12)
        title = QLabel("Mailbox Synchroniseur")
        title.setObjectName("title")
        outer.addWidget(title)
        subtitle = QLabel("Retrouve tes messages dans ta nouvelle boîte mail.")
        subtitle.setObjectName("muted")
        outer.addWidget(subtitle)
        note = QLabel("Version alpha • Copie dans un seul sens • Mots de passe conservés pour cette session uniquement")
        note.setWordWrap(True)
        outer.addWidget(note)
        self.config = QTabWidget()
        accounts_page = QWidget()
        config_layout = QVBoxLayout(accounts_page)
        config_layout.setContentsMargins(0, 0, 0, 0)
        accounts = QHBoxLayout()
        self.source = AccountCard("1  ·  Boîte source")
        self.destination = AccountCard("2  ·  Boîte destination")
        accounts.addWidget(self.source)
        accounts.addWidget(self.destination)
        config_layout.addLayout(accounts)
        controls = QHBoxLayout()
        self.open_button = QPushButton("Ouvrir un profil")
        self.save_button = QPushButton("Enregistrer le profil")
        self.swap_button = QPushButton("Inverser les comptes")
        self.open_button.clicked.connect(self._open)
        self.save_button.clicked.connect(self._save)
        self.swap_button.clicked.connect(self._swap)
        for button in (self.open_button, self.save_button, self.swap_button):
            controls.addWidget(button)
        controls.addStretch()
        config_layout.addLayout(controls)
        engine_box = QGroupBox("Moteur de transfert")
        engine_layout = QVBoxLayout(engine_box)
        engine_row = QHBoxLayout()
        self.engine = QLineEdit(shutil.which("imapsync") or "")
        self.engine.setPlaceholderText("Sélectionner imapsync.exe (Windows) ou l'exécutable imapsync")
        browse = QPushButton("Parcourir…")
        browse.clicked.connect(self._browse)
        engine_row.addWidget(self.engine)
        engine_row.addWidget(browse)
        engine_layout.addLayout(engine_row)
        hint = QLabel("Cette alpha utilise une installation existante d'imapsync. Connexion Google / Microsoft par navigateur prévue ultérieurement.")
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        engine_layout.addWidget(hint)
        config_layout.addWidget(engine_box)
        self.config.addTab(accounts_page, "Comptes et connexion")
        self.folders = FolderSelector()
        self.config.addTab(self.folders, "Dossiers à copier")
        outer.addWidget(self.config)
        self.scope = QLabel("Périmètre : tous les dossiers · Source → destination · Simulation requise avant copie")
        self.scope.setWordWrap(True)
        outer.addWidget(self.scope)
        actions = QHBoxLayout()
        self.login = QPushButton("1. Tester les accès")
        self.preview = QPushButton("2. Simuler")
        self.copy = QPushButton("3. Copier les messages")
        self.copy.setObjectName("primary")
        self.copy.setEnabled(False)
        self.stop = QPushButton("Arrêter")
        self.stop.setEnabled(False)
        self.login.clicked.connect(lambda: self._run(Mode.LOGIN))
        self.preview.clicked.connect(lambda: self._run(Mode.PREVIEW))
        self.copy.clicked.connect(lambda: self._run(Mode.COPY))
        self.stop.clicked.connect(self._stop)
        for button in (self.login, self.preview, self.copy, self.stop):
            actions.addWidget(button)
        outer.addLayout(actions)
        self.status = QLabel("Prêt. Renseigne les comptes et sélectionne le moteur.")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.summary = QLabel("Le bilan apparaîtra à la fin de l'opération.")
        self.summary.setWordWrap(True)
        self.summary.setObjectName("muted")
        outer.addWidget(self.summary)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        outer.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(3000)
        self.log.setMinimumHeight(150)
        self.log.setPlaceholderText("Le journal de la prochaine opération apparaîtra ici.")
        outer.addWidget(self.log, 1)
        footer = QLabel("Les messages déjà copiés restent à destination après un arrêt. Contacts et calendriers non inclus.")
        footer.setWordWrap(True)
        footer.setObjectName("muted")
        outer.addWidget(footer)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        self.setCentralWidget(scroll)
        self.source.changed.connect(self._invalidate)
        self.destination.changed.connect(self._invalidate)
        self.engine.textChanged.connect(self._invalidate)
        self.folders.changed.connect(self._invalidate)

    def _plan(self):
        return Plan(self.source.account(), self.destination.account(), self.engine.text().strip(), self.folders.value())

    def _invalidate(self):
        selected = self.folders.enabled.isChecked()
        self.scope.setText("Périmètre : " + ("dossiers sélectionnés" if selected else "tous les dossiers") + " · Source → destination · Simulation requise")
        self.preview_plan = None
        self.copy.setEnabled(False)
        if not self.runner.active:
            self.status.setText("Configuration modifiée. Une simulation réussie est nécessaire avant la copie.")

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionner le moteur imapsync")
        if path:
            self.engine.setText(path)

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un profil", "", "Profil JSON (*.json)")
        if path:
            try:
                plan = load_profile(Path(path))
                self.source.set_account(plan.source)
                self.destination.set_account(plan.destination)
                self.folders.load(plan.folders)
                # A profile is data, not permission to execute its referenced program.
                self.engine.clear()
                self._invalidate()
                self.status.setText("Profil chargé. Ressaisis les mots de passe et sélectionne ton exécutable imapsync.")
            except (OSError, ValueError) as exc:
                self._problem(str(exc))

    def _save(self):
        try:
            plan = self._plan()
            plan.validate()
            path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sans mots de passe", "migration.json", "Profil JSON (*.json)")
            if path:
                save_profile(Path(path), plan)
                self.status.setText("Profil enregistré sans mots de passe.")
        except (OSError, ValueError) as exc:
            self._problem(str(exc))

    def _swap(self):
        source, dest = self.source.account(), self.destination.account()
        self.source.set_account(dest)
        self.destination.set_account(source)
        self.folders.invert()
        self._invalidate()
        self.status.setText("Comptes inversés. Ressaisis les mots de passe.")

    def _run(self, mode):
        if self.runner.active:
            return
        plan = self._plan()
        if mode == Mode.COPY:
            if self.preview_plan != plan:
                self._problem("Refais une simulation avec ces comptes avant de copier.")
                return
            answer = QMessageBox.question(
                self, "Confirmer la copie", f"Copier les dossiers du périmètre affiché de :\n{plan.source.user} ({plan.source.host})\n\nVers :\n{plan.destination.user} ({plan.destination.host})\n\nLes messages déjà copiés resteront à destination en cas d'arrêt.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.preview_plan = None
        self.copy.setEnabled(False)
        self.log.clear()
        self.summary.setText("Bilan en attente…")
        self.current_plan = plan
        self.current_mode = mode
        self.config.setEnabled(False)
        self.login.setEnabled(False)
        self.preview.setEnabled(False)
        self.stop.setEnabled(True)
        self.progress.setRange(0, 0)
        self.status.setText({Mode.LOGIN: "Test des accès en cours…", Mode.PREVIEW: "Simulation en cours… aucun message n'est copié.", Mode.COPY: "Copie en cours…"}[mode])
        try:
            self.runner.start(plan, mode, (self.source.password.text(), self.destination.password.text()))
        except (OSError, ValueError) as exc:
            self._done(False, str(exc))
            self._problem(str(exc))
            return

    def _stop(self):
        self.stop.setEnabled(False)
        self.runner.stop()
        self.status.setText("Arrêt en cours…")

    def _line(self, text):
        self.log.appendPlainText(text)

    def _done(self, ok, message):
        self.config.setEnabled(True)
        self.login.setEnabled(True)
        self.preview.setEnabled(True)
        self.stop.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(1 if ok else 0)
        if ok and self.current_mode == Mode.PREVIEW:
            self.preview_plan = self.current_plan
            message = "Simulation terminée. Vérifie le journal, puis lance la copie."
        self.copy.setEnabled(self.preview_plan is not None)
        self.status.setText(message)
        self.summary.setText(self.runner.report.text())
        self._line(message)
        if self.close_after_run:
            self.close()

    def _problem(self, message):
        self.status.setText(message)
        QMessageBox.warning(self, "Configuration à vérifier", message)

    def closeEvent(self, event):
        if self.runner.active:
            event.ignore()
            if QMessageBox.question(self, "Opération en cours", "Arrêter l'opération puis fermer l'application ?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.close_after_run = True
                self._stop()
        else:
            self.source.password.clear()
            self.destination.password.clear()
            event.accept()
