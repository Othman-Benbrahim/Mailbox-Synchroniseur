"""OAuth 2.0 for IMAP, Microsoft first. No embedded application identity.

The user registers their own application and provides its client identifier;
nothing about this project is registered with a provider. The flow is the one
recommended for a native application: authorization code with PKCE, system
browser, and a redirect to a loopback address bound on a random free port.
No client secret is used: a desktop application cannot keep one.

The access token is what the engine needs. It is written to a file in the
per-run temporary directory rather than passed on a command line, exactly as
passwords are passed through the environment today.
"""
from dataclasses import dataclass
import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request

MICROSOFT = "microsoft"
GOOGLE = "google"

PROVIDERS = {
    MICROSOFT: {
        "label": "Microsoft (Outlook.com, Microsoft 365)",
        "authorize": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scopes": ("offline_access", "https://outlook.office.com/IMAP.AccessAsUser.All"),
        "secret_required": False,
    },
    GOOGLE: {
        "label": "Google (Gmail)",
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scopes": ("https://mail.google.com/",),
        "secret_required": True,   # Google issues a "secret" even for desktop clients
    },
}


class OAuthError(Exception):
    """Human-readable failure. Never contains a token or a secret."""


@dataclass(frozen=True)
class Token:
    access_token: str
    expires_in: int | None = None
    refresh_token: str | None = None

    def write(self, directory, name="oauth-token"):
        """Write the access token where the engine can read it, readable by this
        user only. imapsync takes the first line of the file."""
        path = os.path.join(str(directory), name)
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(self.access_token + "\n")
        return path


def challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


PAGE = ("<!doctype html><html lang=fr><meta charset=utf-8>"
        "<title>Mailbox Synchroniseur</title>"
        "<body style='font-family:sans-serif;padding:2em'>"
        "<h1>{title}</h1><p>{message}</p>"
        "<p>Tu peux fermer cet onglet et revenir à l'application.</p>")


class _Handler(http.server.BaseHTTPRequestHandler):
    result = None

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        type(self).result = {k: v[0] for k, v in query.items()}
        ok = "code" in type(self).result
        body = PAGE.format(title="Autorisation reçue" if ok else "Autorisation refusée",
                           message="L'application peut maintenant accéder à cette boîte."
                           if ok else "Aucun accès n'a été accordé.")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *args):
        pass          # the URL carries the authorization code; never log it


def authorization_url(provider: str, client_id: str, redirect_uri: str, state: str,
                      verifier: str, login_hint: str = "") -> str:
    config = PROVIDERS[provider]
    parameters = {
        "client_id": client_id, "response_type": "code", "redirect_uri": redirect_uri,
        "scope": " ".join(config["scopes"]), "state": state,
        "code_challenge": challenge(verifier), "code_challenge_method": "S256",
    }
    if login_hint:
        parameters["login_hint"] = login_hint
    if provider == GOOGLE:
        # Without these, Google returns no refresh token on a repeat authorization.
        parameters["access_type"] = "offline"
        parameters["prompt"] = "consent"
    return config["authorize"] + "?" + urllib.parse.urlencode(parameters)


def exchange(provider: str, client_id: str, code: str, redirect_uri: str, verifier: str,
             client_secret: str = "", timeout: float = 30) -> Token:
    config = PROVIDERS[provider]
    data = {"client_id": client_id, "code": code, "redirect_uri": redirect_uri,
            "grant_type": "authorization_code", "code_verifier": verifier}
    if client_secret:
        data["client_secret"] = client_secret
    request = urllib.request.Request(
        config["token"], data=urllib.parse.urlencode(data).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise OAuthError(describe(exc)) from None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise OAuthError(f"Échange du jeton impossible ({exc}).") from None
    if "access_token" not in payload:
        raise OAuthError("Le fournisseur n'a pas renvoyé de jeton d'accès.")
    return Token(payload["access_token"], payload.get("expires_in"), payload.get("refresh_token"))


def describe(error) -> str:
    """Provider error, without echoing anything secret."""
    try:
        content = json.loads(error.read().decode("utf-8"))
        code = content.get("error", "")
        detail = content.get("error_description", "").splitlines()[0][:200]
    except Exception:
        code, detail = "", ""
    known = {
        "invalid_client": "Identifiant d'application refusé : vérifie le client_id (et le secret pour Google).",
        "invalid_grant": "Autorisation expirée ou déjà utilisée. Recommence la connexion.",
        "unauthorized_client": "Cette application n'est pas autorisée pour ce type de connexion : "
                               "active « Allow public client flows » côté Microsoft.",
        "invalid_scope": "Les permissions demandées ne sont pas accordées à cette application.",
        "access_denied": "Autorisation refusée par l'utilisateur ou par l'administrateur du domaine.",
    }
    return known.get(code) or (f"Le fournisseur a refusé la demande ({code or error.code}). {detail}".strip())


def authorize(provider: str, client_id: str, client_secret: str = "", login_hint: str = "",
              open_browser=None, timeout: float = 300) -> Token:
    """Full interactive flow. Blocks until the browser comes back or the timeout
    expires; run it off the GUI thread."""
    if provider not in PROVIDERS:
        raise OAuthError("Fournisseur OAuth inconnu.")
    if not client_id.strip():
        raise OAuthError("Renseigne l'identifiant d'application (client_id) de ton inscription.")
    if PROVIDERS[provider]["secret_required"] and not client_secret.strip():
        raise OAuthError("Google exige aussi le secret client de ton inscription.")
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(16)
    port = free_port()
    redirect_uri = f"http://localhost:{port}/"
    handler = type("Handler", (_Handler,), {"result": None})
    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    server.timeout = 1
    url = authorization_url(provider, client_id.strip(), redirect_uri, state, verifier, login_hint)
    (open_browser or _default_browser)(url)
    finished = threading.Event()

    def serve():
        import time
        deadline = time.monotonic() + timeout
        while not finished.is_set() and time.monotonic() < deadline:
            server.handle_request()
            if handler.result is not None:
                return
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    thread.join(timeout + 2)
    finished.set()
    server.server_close()
    result = handler.result
    if result is None:
        raise OAuthError("Aucune réponse du navigateur : autorisation abandonnée ou expirée.")
    if result.get("state") != state:
        raise OAuthError("Réponse d'autorisation inattendue ; la connexion a été abandonnée.")
    if "code" not in result:
        raise OAuthError(f"Autorisation refusée ({result.get('error', 'sans motif')}).")
    return exchange(provider, client_id.strip(), result["code"], redirect_uri, verifier,
                    client_secret.strip())


def _default_browser(url):
    import webbrowser
    if not webbrowser.open(url):
        raise OAuthError("Impossible d'ouvrir le navigateur système.")
