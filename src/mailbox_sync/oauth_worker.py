"""Runs the browser authorization off the GUI thread. Tokens stay in memory."""
from PySide6.QtCore import QThread, Signal
from .oauth import OAuthError, authorize


class OAuthWorker(QThread):
    obtained = Signal(str, object)   # access token, expires_in
    failed = Signal(str)

    def __init__(self, provider, client_id, client_secret="", login_hint="", parent=None,
                 authorizer=authorize):
        super().__init__(parent)
        self._provider = provider
        self._client_id = client_id
        self._client_secret = client_secret
        self._login_hint = login_hint
        self._authorizer = authorizer

    def run(self):
        try:
            token = self._authorizer(self._provider, self._client_id, self._client_secret,
                                     self._login_hint)
        except OAuthError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Connexion interrompue : {type(exc).__name__}.")
        else:
            self.obtained.emit(token.access_token, token.expires_in)
        finally:
            self._client_secret = ""
