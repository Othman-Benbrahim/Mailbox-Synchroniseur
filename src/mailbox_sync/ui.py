from datetime import datetime, timezone
from pathlib import Path
import shutil
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QTabWidget,
    QInputDialog,
)
from . import __version__
from .models import Account, Mode, Plan
from .profiles import load_profile, save_profile
from .runner import Runner
from .folder_selector import FolderSelector
from .filter_selector import FilterSelector
from .mirror_selector import MirrorSelector
from .discovery_worker import DiscoveryWorker
from .oauth import PROVIDERS
from .oauth_worker import OAuthWorker
from .history_view import HistoryView
from . import history

STYLE = """
/* Every widget the application uses states its own colours: on a system in dark
   mode, anything left out would be dark text on a dark background. */
QWidget { font-family: 'Segoe UI', 'DejaVu Sans'; font-size: 13px; color: #192d42; }
QMainWindow, QDialog, QScrollArea, QSplitter, #page { background: #f3f6fa; }
QMessageBox, QInputDialog, QFileDialog { background: #f3f6fa; color: #192d42; }
QGroupBox { background: white; border: 1px solid #d6dfe9; border-radius: 10px;
            margin-top: 18px; padding: 20px 14px 14px; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 6px; color: #192d42; }
QLabel, QCheckBox, QRadioButton { background: transparent; color: #192d42; }
QCheckBox:disabled, QLabel:disabled { color: #7b8898; }
QLineEdit, QSpinBox, QComboBox, QDateEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox {
    background: white; color: #192d42; padding: 8px; border: 1px solid #b8c8d9; border-radius: 5px; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus { border: 1px solid #14736a; }
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled, QDateEdit:disabled {
    background: #edf0f4; color: #7b8898; }
QComboBox QAbstractItemView, QCalendarWidget QAbstractItemView, QListView, QTreeView {
    background: white; color: #192d42; selection-background-color: #146f66;
    selection-color: white; border: 1px solid #b8c8d9; }
QCalendarWidget QWidget { background: white; color: #192d42; }
QCalendarWidget QToolButton { color: #192d42; background: white; }
QTableWidget, QTableView, QListWidget { background: white; color: #192d42;
    alternate-background-color: #f3f6fa; gridline-color: #d6dfe9;
    selection-background-color: #146f66; selection-color: white; }
QHeaderView::section { background: #edf2f7; color: #192d42; border: none;
    border-right: 1px solid #d6dfe9; border-bottom: 1px solid #d6dfe9; padding: 6px; }
QTabWidget::pane { background: white; border: 1px solid #d6dfe9; border-radius: 8px; }
QTabBar::tab { background: #e4ebf2; color: #192d42; padding: 8px 14px;
    border: 1px solid #d6dfe9; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background: white; font-weight: bold; }
QTabBar::tab:disabled { color: #7b8898; }
QPushButton { padding: 9px 15px; background: white; color: #192d42;
    border: 1px solid #b8c8d9; border-radius: 6px; }
QPushButton:hover { background: #e7f2ef; border-color: #14736a; }
QPushButton:disabled { color: #7b8898; background: #edf0f4; border-color: #d7dfe7; }
QPushButton#primary { background: #146f66; color: white; border: none; font-weight: bold; }
QPushButton#primary:disabled { background: #baccc9; color: #f5f8f7; }
QPlainTextEdit#log { background: #172738; color: #e3edf5; border: none; border-radius: 7px;
                 font-family: 'Consolas', monospace; font-size: 12px; padding: 10px; }
QProgressBar { border: none; background: #dfe8ef; color: #192d42; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #188779; }
QScrollBar:vertical, QScrollBar:horizontal { background: #edf0f4; border: none; }
QScrollBar::handle { background: #b8c8d9; border-radius: 4px; }
QToolTip { background: white; color: #192d42; border: 1px solid #b8c8d9; }
QLabel#title { font-size: 27px; font-weight: bold; color: #192d42; }
QLabel#muted { color: #52687c; }
"""


class AccountCard(QGroupBox):
    changed = Signal()

    def __init__(self, title):
        super().__init__(title)
        self.token = ""
        self.worker = None
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
        self.auth = QComboBox()
        self.auth.addItem("Mot de passe ou mot de passe d'application", "basic")
        for key, config in PROVIDERS.items():
            self.auth.addItem(f"OAuth — {config['label']}", key)
        self.client_id = QLineEdit()
        self.client_id.setPlaceholderText("Identifiant d'application (client_id) de ton inscription")
        self.client_secret = QLineEdit()
        self.client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_secret.setPlaceholderText("Secret client (Google uniquement)")
        self.connect_button = QPushButton("Se connecter dans le navigateur…")
        self.oauth_status = QLabel("Compte non connecté.")
        self.oauth_status.setWordWrap(True)
        self.oauth_status.setObjectName("muted")
        self.show_password = QCheckBox("Afficher")
        self.show_password.toggled.connect(lambda show: self.password.setEchoMode(
            QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password))
        for label, field in (("Serveur", self.host), ("Identifiant", self.user),
                             ("Authentification", self.auth),
                             ("Mot de passe", self.password), ("Connexion", self.security),
                             ("Port", self.port)):
            layout.addRow(label, field)
        layout.addRow("", self.show_password)
        layout.addRow("client_id", self.client_id)
        layout.addRow("Secret client", self.client_secret)
        layout.addRow("", self.connect_button)
        layout.addRow("", self.oauth_status)
        self.auth.currentIndexChanged.connect(self._auth_changed)
        self.connect_button.clicked.connect(self._connect)
        for field in (self.client_id, self.client_secret):
            field.textChanged.connect(self._forget_token)
        self.user.textChanged.connect(self._forget_token)
        self._auth_changed()
        for field in (self.host, self.user, self.password):
            field.textChanged.connect(self.changed)
        self.port.valueChanged.connect(self.changed)
        self.security.currentIndexChanged.connect(self.changed)

    def _security_changed(self):
        self.port.setValue(993 if self.security.currentData() == "SSL" else 143)

    def _auth_changed(self):
        provider = self.auth.currentData()
        oauth = provider != "basic"
        secret_needed = oauth and PROVIDERS.get(provider, {}).get("secret_required", False)
        for widget in (self.password, self.show_password):
            widget.setVisible(not oauth)
        for widget in (self.client_id, self.connect_button, self.oauth_status):
            widget.setVisible(oauth)
        self.client_secret.setVisible(secret_needed)
        # isVisible() is False while the window has not been shown yet, so the
        # intended state is used rather than the current one.
        form = self.layout()
        for widget, wanted in ((self.password, not oauth), (self.client_id, oauth),
                               (self.client_secret, secret_needed)):
            label = form.labelForField(widget)
            if label is not None:
                label.setVisible(wanted)
        if oauth:
            self.password.clear()
        self._forget_token()

    def _forget_token(self):
        """Any change to the identity or to the registration drops the token."""
        if self.token:
            self.token = ""
            self.oauth_status.setText("Compte non connecté.")
        self.changed.emit()

    def _connect(self):
        if self.worker is not None:
            return
        provider = self.auth.currentData()
        if provider == "basic":
            return
        self.connect_button.setEnabled(False)
        self.oauth_status.setText("Connexion en cours dans le navigateur…")
        self.worker = OAuthWorker(provider, self.client_id.text().strip(),
                                  self.client_secret.text().strip(), self.user.text().strip(), self)
        self.worker.obtained.connect(self._connected)
        self.worker.failed.connect(self._connection_failed)
        self.worker.finished.connect(self._connection_done)
        self.worker.start()

    def _connection_done(self):
        worker, self.worker = self.worker, None
        if worker is not None:
            worker.deleteLater()
        self.connect_button.setEnabled(True)

    def _connected(self, token, expires_in):
        self.token = token
        minutes = f" (valable environ {int(expires_in) // 60} minutes)" if expires_in else ""
        self.oauth_status.setText(f"Compte connecté{minutes}. Le jeton reste en mémoire pour cette session.")
        self.changed.emit()

    def _connection_failed(self, message):
        self.token = ""
        self.oauth_status.setText(message)
        self.changed.emit()

    def secret(self):
        """The secret handed to the engine: a password, or an OAuth access token."""
        return self.token if self.auth.currentData() != "basic" else self.password.text()

    def account(self):
        provider = self.auth.currentData()
        return Account(self.host.text().strip(), self.user.text().strip(),
                       self.port.value(), self.security.currentData(),
                       "basic" if provider == "basic" else "oauth",
                       "" if provider == "basic" else provider)

    def set_account(self, account):
        self.host.setText(account.host)
        self.user.setText(account.user)
        self.security.setCurrentIndex(self.security.findData(account.security))
        self.port.setValue(account.port)
        self.auth.setCurrentIndex(self.auth.findData(account.provider if account.oauth else "basic"))
        self.password.clear()
        self.show_password.setChecked(False)
        self._forget_token()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Mailbox Synchroniseur — {__version__}")
        self.resize(1060, 840)
        self.setMinimumSize(780, 620)
        self.setStyleSheet(STYLE)
        self.preview_plan = None
        self.preview_report = None
        self.current_plan = None
        self.current_mode = None
        self.close_after_run = False
        self.discovery = None
        self.started_at = None
        self.history_directory = None
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
        hint = QLabel("Cette alpha utilise une installation existante d'imapsync. La connexion OAuth "
                      "par navigateur exige une inscription d'application à ton nom : voir docs/OAUTH.md.")
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        engine_layout.addWidget(hint)
        config_layout.addWidget(engine_box)
        self.config.addTab(accounts_page, "Comptes et connexion")
        self.folders = FolderSelector()
        self.config.addTab(self.folders, "Dossiers à copier")
        self.filters = FilterSelector()
        self.config.addTab(self.filters, "Filtres")
        self.mirror = MirrorSelector()
        self.config.addTab(self.mirror, "Miroir")
        self.history = HistoryView(self.history_directory)
        self.history.reuse_requested.connect(self._reuse)
        self.config.addTab(self.history, "Historique")
        outer.addWidget(self.config)
        self.scope = QLabel("Périmètre : tous les dossiers · Filtres : aucun · Source → destination · Simulation requise avant copie")
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
        self.log.setObjectName("log")
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
        self.folders.discover_requested.connect(self._discover)
        self.filters.changed.connect(self._invalidate)
        self.mirror.changed.connect(self._invalidate)

    def _discover(self):
        if self.runner.active or self.discovery is not None:
            return
        try:
            source, destination = self.source.account(), self.destination.account()
            source.validate()
            destination.validate()
        except ValueError as exc:
            self._problem(str(exc))
            return
        passwords = (self.source.secret(), self.destination.secret())
        if not all(passwords):
            self._problem("Renseigne les deux mots de passe, ou connecte les comptes OAuth, "
                          "avant de découvrir les dossiers.")
            return
        self.discovery = DiscoveryWorker(source, destination, passwords, self)
        self.discovery.proposed.connect(self._discovered)
        self.discovery.failed.connect(self._discovery_failed)
        self.config.setEnabled(False)
        for button in (self.login, self.preview, self.copy):
            button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status.setText("Découverte des dossiers en cours… aucun message n'est lu ni copié.")
        self.discovery.start()

    def _discovery_done(self):
        worker, self.discovery = self.discovery, None
        if worker is not None:
            worker.wait()
            worker.deleteLater()
        self.config.setEnabled(True)
        self.login.setEnabled(True)
        self.preview.setEnabled(True)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)

    def _discovered(self, proposals):
        self._discovery_done()
        self.folders.apply_proposal(proposals)
        kept = sum(1 for p in proposals if p.mapping is not None)
        excluded = len(proposals) - kept
        self._invalidate()
        self.status.setText(f"Proposition : {kept} dossier(s) à copier, {excluded} exclu(s). "
                            "Vérifie le tableau et les raisons, puis lance une simulation.")

    def _discovery_failed(self, message):
        self._discovery_done()
        self._problem(message)

    def _plan(self):
        mirror, expunge = self.mirror.value()
        return Plan(self.source.account(), self.destination.account(), self.engine.text().strip(),
                    self.folders.value(), self.filters.value(), mirror, expunge)

    def _invalidate(self):
        selected = self.folders.enabled.isChecked()
        mirror, expunge = self.mirror.value()
        self.scope.setText("Périmètre : " + ("dossiers sélectionnés" if selected else "tous les dossiers")
                           + " · Filtres : " + self.filters.value().describe()
                           + " · " + ("MIROIR ACTIF : suppressions à destination"
                                      + (" avec vidage définitif" if expunge else "")
                                      if mirror else "Source → destination")
                           + " · Simulation requise")
        self.preview_plan = None
        self.preview_report = None
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
                self.filters.load(plan.filters)
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
            if plan.destructive and not self._confirm_deletions(plan):
                return
            answer = QMessageBox.question(
                self, "Confirmer la copie", f"Copier les dossiers du périmètre affiché de :\n{plan.source.user} ({plan.source.host})\n\nVers :\n{plan.destination.user} ({plan.destination.host})\n\nFiltres : {plan.filters.describe()}\n\nLes messages déjà copiés resteront à destination en cas d'arrêt.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.preview_plan = None
        self.preview_report = None
        self.copy.setEnabled(False)
        self.log.clear()
        self.summary.setText("Bilan en attente…")
        self.current_plan = plan
        self.current_mode = mode
        self.started_at = datetime.now(timezone.utc)
        self.config.setEnabled(False)
        self.login.setEnabled(False)
        self.preview.setEnabled(False)
        self.stop.setEnabled(True)
        self.progress.setRange(0, 0)
        self.status.setText({Mode.LOGIN: "Test des accès en cours…", Mode.PREVIEW: "Simulation en cours… aucun message n'est copié.", Mode.COPY: "Copie en cours…"}[mode])
        try:
            self.runner.start(plan, mode, (self.source.secret(), self.destination.secret()))
        except (OSError, ValueError) as exc:
            self._done(False, str(exc))
            self._problem(str(exc))
            return

    def _confirm_deletions(self, plan):
        """Second gate, for destructive runs only: show the number of deletions the
        simulation announced and require the user to type a word."""
        announced = self.preview_report.marked_deleted if self.preview_report else None
        if announced is None:
            self._problem("Refais une simulation avec le miroir activé avant de copier.")
            return False
        if announced == 0:
            return True
        effect = ("Ces messages seront définitivement retirés de la destination."
                  if plan.expunge else
                  "Ces messages seront marqués « supprimé » à destination ; ils restent "
                  "récupérables tant que tu ne vides pas la boîte.")
        typed, accepted = QInputDialog.getText(
            self, "Confirmer les suppressions",
            f"La simulation annonce {announced} message(s) à supprimer à destination "
            f"({plan.destination.user} sur {plan.destination.host}).\n\n{effect}\n"
            "La boîte source n'est pas touchée.\n\n"
            "Pour confirmer, saisis SUPPRIMER en majuscules :")
        if not accepted:
            return False
        if typed.strip() != "SUPPRIMER":
            self._problem("Confirmation incorrecte : aucune suppression n'a été lancée.")
            return False
        return True

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
            self.preview_report = self.runner.report
            message = "Simulation terminée. Vérifie le journal, puis lance la copie."
        self.copy.setEnabled(self.preview_plan is not None)
        self._record(ok, message)
        self.status.setText(message)
        self.summary.setText(self.runner.report.text())
        self._line(message)
        if self.close_after_run:
            self.close()

    def _record(self, ok, message):
        """A finished run is kept locally, without secrets. A failure to write is
        reported once and never blocks the operation itself."""
        if self.current_plan is None or self.started_at is None:
            return
        try:
            entry = history.build(self.current_plan, self.runner.report, ok, message, self.started_at)
            history.save(entry, self.history_directory)
        except (OSError, ValueError) as exc:
            self._line(f"L'opération n'a pas pu être ajoutée à l'historique : {exc}")
            return
        finally:
            self.started_at = None
        self.history.refresh()

    def _reuse(self, entry):
        """Reuse the scope of a past run: folders and filters only, never a secret."""
        from .models import Filters
        self.folders.load(history.mappings_of(entry))
        try:
            self.filters.load(Filters(**entry.filters))
        except (TypeError, ValueError):
            self.filters.load(Filters())
        self.config.setCurrentWidget(self.folders)
        self._invalidate()
        self.status.setText("Périmètre et filtres repris de l'historique. "
                            "Vérifie les comptes, ressaisis les mots de passe, puis simule.")

    def _problem(self, message):
        self.status.setText(message)
        QMessageBox.warning(self, "Configuration à vérifier", message)

    def closeEvent(self, event):
        if self.discovery is not None:
            event.ignore()
            self.status.setText("Attends la fin de la découverte des dossiers avant de fermer.")
            return
        if self.runner.active:
            event.ignore()
            if QMessageBox.question(self, "Opération en cours", "Arrêter l'opération puis fermer l'application ?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self.close_after_run = True
                self._stop()
        else:
            for card in (self.source, self.destination):
                card.password.clear()
                card.token = ""
            event.accept()
