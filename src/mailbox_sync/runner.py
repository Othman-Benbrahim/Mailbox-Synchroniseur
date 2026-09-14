"""Asynchronous external engine, with no shell and no persistent raw logs."""
import codecs
import tempfile
from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal
from .engine import Redactor, command, outcome
from .models import Mode, validate_passwords
from .report import MigrationReport


class Runner(QObject):
    line = Signal(str)
    done = Signal(bool, str)
    started = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.started.connect(self._started)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._error)
        self.kill_timer = QTimer(self)
        self.kill_timer.setSingleShot(True)
        self.kill_timer.timeout.connect(self.process.kill)
        self.active = False
        self.cancelled = False
        self._temp = None
        self._buffer = ""
        self._discard = False
        self._redactor = Redactor()
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.report = MigrationReport()

    def start(self, plan, mode, passwords):
        if self.active:
            raise ValueError("Une opération est déjà en cours.")
        self.report = MigrationReport(mode=Mode(mode))
        validate_passwords(passwords)
        program, args = command(plan, mode)
        self._temp = tempfile.TemporaryDirectory(prefix="mailbox-run-")
        env = QProcessEnvironment.systemEnvironment()
        for name in env.keys():
            if name.startswith("IMAPSYNC_"):
                env.remove(name)
        for i, password in enumerate(passwords, 1):
            env.insert(f"IMAPSYNC_PASSWORD{i}", password)
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(self._temp.name)
        self._redactor = Redactor(passwords)
        self._decoder.reset()
        self._buffer = ""
        self._discard = False
        self.cancelled = False
        self.active = True
        self.process.start(program, args)

    def _started(self):
        # The child already has its environment; do not retain secrets in QProcess.
        self.process.setProcessEnvironment(QProcessEnvironment())
        self.process.closeWriteChannel()
        self.started.emit()

    def stop(self):
        if self.active:
            self.cancelled = True
            self.line.emit("Arrêt demandé ; les messages déjà copiés restent à destination.")
            self.process.terminate()
            self.kill_timer.start(3000)

    def _consume(self, text):
        for segment in text.splitlines(keepends=True):
            ended = segment.endswith(("\n", "\r"))
            if not self._discard:
                self._buffer += segment
                if len(self._buffer) > 65536:
                    self._buffer = ""
                    self._discard = True
                    self.line.emit("[Ligne de journal trop longue omise]")
            if ended:
                if not self._discard:
                    self._emit_line(self._buffer)
                self._buffer = ""
                self._discard = False

    def _emit_line(self, text):
        self.report.feed(text)
        self.line.emit(self._redactor.clean(text))

    def _read(self):
        self._consume(self._decoder.decode(bytes(self.process.readAllStandardOutput())))

    def _error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._complete(False, "Impossible de lancer imapsync. Vérifie le fichier, ses permissions et ses dépendances.")

    def _finished(self, code, status):
        if not self.active:
            return
        self._read()
        self._consume(self._decoder.decode(b"", final=True))
        if self._buffer and not self._discard:
            self._emit_line(self._buffer)
        self.report.exit_code = code
        self.report.cancelled = self.cancelled
        self.report.crashed = status == QProcess.ExitStatus.CrashExit
        if self.cancelled:
            self._complete(False, "Opération arrêtée. Une copie peut être partielle ; refais une simulation avant de reprendre.")
        elif status == QProcess.ExitStatus.CrashExit:
            self._complete(False, "Le moteur s'est interrompu anormalement ; consulte le journal.")
        else:
            self._complete(code == 0, outcome(code))

    def _complete(self, ok, message):
        if not self.active:
            return
        if ok and (self.report.errors or (self.report.mode == Mode.COPY and
                                          (self.report.missing or self.report.unidentified))):
            ok = False
            message = "Le bilan signale des erreurs ou des messages non transférés. Consulte le journal."
        self.kill_timer.stop()
        self.active = False
        self.process.setProcessEnvironment(QProcessEnvironment())
        self._redactor = Redactor()
        self._buffer = ""
        if self._temp:
            try:
                self._temp.cleanup()
            except OSError:
                message += " Le dossier temporaire n'a pas pu être nettoyé."
            self._temp = None
        self.done.emit(ok, message)
