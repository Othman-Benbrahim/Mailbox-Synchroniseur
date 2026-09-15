"""Phase 4, lot 4a: OAuth for IMAP. No application identity is embedded here.

The point of these tests is that a token is a secret like any other: never on a
command line, never in a profile, never in the log, dropped when the identity or
the registration changes.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import pytest
from mailbox_sync.engine import Redactor, command
from mailbox_sync.models import Account, Mode, Plan, validate_passwords
from mailbox_sync.oauth import (GOOGLE, MICROSOFT, OAuthError, PROVIDERS, Token, authorization_url,
                                challenge, describe)
from mailbox_sync.oauth_worker import OAuthWorker
from mailbox_sync.profiles import load_profile, save_profile
from mailbox_sync.runner import Runner
from mailbox_sync.ui import Window

TOKEN = "ya29.a0-FAKE-access-token"


def account(provider=MICROSOFT, **options):
    return Account("outlook.example", "moi@exemple.fr", 993, "SSL", "oauth", provider, **options)


def plan(source=None, destination=None):
    return Plan(source or account(), destination or Account("dest.example", "autre"), sys.executable)


def test_account_validation_pairs_auth_and_provider():
    account().validate()
    Account("a.example", "u").validate()
    for bad in (Account("a.example", "u", 993, "SSL", "oauth", ""),
                Account("a.example", "u", 993, "SSL", "oauth", "yahoo"),
                Account("a.example", "u", 993, "SSL", "basic", "google"),
                Account("a.example", "u", 993, "SSL", "jeton", "")):
        with pytest.raises(ValueError):
            bad.validate()


def test_a_profile_never_carries_a_token(tmp_path):
    path = tmp_path / "profil.json"
    save_profile(path, plan())
    text = path.read_text(encoding="utf-8")
    assert TOKEN not in text and "token" not in text.lower() and "password" not in text.lower()
    data = json.loads(text)
    assert data["source"]["auth"] == "oauth" and data["source"]["provider"] == "microsoft"
    assert load_profile(path) == plan()


def test_older_profiles_still_load_as_password_accounts(tmp_path):
    path = tmp_path / "v2.json"
    save_profile(path, plan())
    data = json.loads(path.read_text(encoding="utf-8"))
    for side in ("source", "destination"):
        data[side].pop("auth")
        data[side].pop("provider")
    path.write_text(json.dumps(data), encoding="utf-8")
    restored = load_profile(path)
    assert restored.source.auth == "basic" and not restored.source.oauth


def test_the_token_is_never_an_argument(tmp_path):
    token_file = tmp_path / "jeton"
    token_file.write_text(TOKEN + "\n", encoding="utf-8")
    _, args = command(plan(), Mode.COPY, (str(token_file), None))
    assert TOKEN not in " ".join(args)
    assert args[args.index("--oauthaccesstoken1") + 1] == str(token_file)
    assert "--oauthaccesstoken2" not in args
    assert not any(a.startswith("--password") for a in args)


def test_an_oauth_account_without_a_token_file_is_refused():
    with pytest.raises(ValueError, match="OAuth"):
        command(plan(), Mode.COPY)
    with pytest.raises(ValueError, match="OAuth"):
        command(plan(), Mode.COPY, (None, None))


def test_token_file_is_readable_by_its_owner_only(tmp_path):
    path = Token(TOKEN).write(tmp_path)
    assert open(path, encoding="utf-8").read() == TOKEN + "\n"
    if os.name == "posix":
        assert os.stat(path).st_mode & 0o777 == 0o600


def test_validate_passwords_accepts_a_token_and_refuses_an_empty_one():
    validate_passwords((TOKEN, "mot-de-passe"), plan())
    for secrets in (("", "mot-de-passe"), ("jeton avec espace", "mot-de-passe")):
        with pytest.raises(ValueError):
            validate_passwords(secrets, plan())
    with pytest.raises(ValueError):
        validate_passwords(("jeton", ""), plan())


def test_authorization_url_is_a_pkce_request_without_a_secret():
    url = authorization_url(MICROSOFT, "client-123", "http://localhost:5000/", "state-abc",
                            "v" * 64, "moi@exemple.fr")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert url.startswith(PROVIDERS[MICROSOFT]["authorize"])
    assert query["response_type"] == ["code"] and query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [challenge("v" * 64)]
    assert "v" * 64 not in url                      # the verifier is never sent at this step
    assert "client_secret" not in query
    assert query["scope"] == ["offline_access https://outlook.office.com/IMAP.AccessAsUser.All"]
    assert query["redirect_uri"] == ["http://localhost:5000/"]
    assert query["login_hint"] == ["moi@exemple.fr"]
    google = urllib.parse.parse_qs(urllib.parse.urlparse(
        authorization_url(GOOGLE, "c", "http://localhost:1/", "s", "v" * 64)).query)
    assert google["scope"] == ["https://mail.google.com/"]
    assert google["access_type"] == ["offline"] and google["prompt"] == ["consent"]


def fake_browser(store):
    def opener(url):
        store.append(url)
    return opener


def test_authorize_refuses_a_missing_registration():
    with pytest.raises(OAuthError, match="client_id"):
        from mailbox_sync.oauth import authorize
        authorize(MICROSOFT, "  ")
    with pytest.raises(OAuthError, match="secret"):
        from mailbox_sync.oauth import authorize
        authorize(GOOGLE, "client-123")
    with pytest.raises(OAuthError, match="inconnu"):
        from mailbox_sync.oauth import authorize
        authorize("yahoo", "client-123")


def run_flow(monkeypatch, response=None, reply=None, timeout=15):
    """Drive the real loopback server with a real HTTP request from another thread."""
    import threading
    import urllib.request
    from mailbox_sync import oauth
    exchanged = {}

    def fake_exchange(provider, client_id, code, redirect_uri, verifier, client_secret="", **kw):
        exchanged.update(provider=provider, code=code, verifier=verifier, redirect=redirect_uri)
        return Token(TOKEN, 3599, "refresh")
    monkeypatch.setattr(oauth, "exchange", fake_exchange)
    seen = []

    def opener(url):
        seen.append(url)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        answer = dict(reply or {"code": "the-code", "state": None})
        if answer.get("state") is None:          # None means "echo the real state"
            answer["state"] = query["state"][0]
        target = query["redirect_uri"][0] + "?" + urllib.parse.urlencode(answer)

        def call():
            try:
                urllib.request.urlopen(target, timeout=5).read()
            except Exception:
                pass
        threading.Thread(target=call, daemon=True).start()
    token = oauth.authorize(MICROSOFT, "client-123", open_browser=opener, timeout=timeout)
    return token, exchanged, seen


def test_full_loopback_flow_exchanges_the_code(monkeypatch):
    token, exchanged, seen = run_flow(monkeypatch)
    assert token.access_token == TOKEN and token.expires_in == 3599
    assert exchanged["code"] == "the-code" and exchanged["provider"] == MICROSOFT
    assert exchanged["redirect"].startswith("http://localhost:")
    assert len(exchanged["verifier"]) >= 43       # PKCE verifier, RFC 7636 minimum
    assert seen and "code_challenge=" in seen[0]


def test_a_mismatched_state_is_rejected(monkeypatch):
    with pytest.raises(OAuthError, match="inattendue"):
        run_flow(monkeypatch, reply={"code": "the-code", "state": "forged"})


def test_a_refusal_is_reported(monkeypatch):
    with pytest.raises(OAuthError, match="refusée"):
        run_flow(monkeypatch, reply={"error": "access_denied", "state": None})


def test_no_browser_answer_times_out():
    from mailbox_sync import oauth
    with pytest.raises(OAuthError, match="Aucune réponse"):
        oauth.authorize(MICROSOFT, "client-123", open_browser=lambda url: None, timeout=0.5)


class FakeHTTPError(urllib.error.HTTPError):
    def __init__(self, payload, code=400):
        self._payload = json.dumps(payload).encode()
        super().__init__("https://token", code, "Bad Request", {}, None)

    def read(self):
        return self._payload


@pytest.mark.parametrize("code,expected", [
    ("invalid_client", "client_id"), ("invalid_grant", "expirée"),
    ("unauthorized_client", "public client flows"), ("access_denied", "refusée"),
])
def test_provider_errors_are_translated(code, expected):
    assert expected in describe(FakeHTTPError({"error": code, "error_description": "détail"}))


def test_an_unknown_provider_error_keeps_its_detail():
    text = describe(FakeHTTPError({"error": "weird_thing", "error_description": "quelque chose"}))
    assert "weird_thing" in text and "quelque chose" in text


def test_the_token_is_redacted_from_the_log():
    assert TOKEN not in Redactor((TOKEN,)).clean(f"AUTHENTICATE XOAUTH2 {TOKEN}")


def test_runner_writes_the_token_to_a_file_and_keeps_it_out_of_the_environment(app, until, tmp_path, monkeypatch):
    script = tmp_path / "engine.py"
    script.write_text('''import os, sys
assert "IMAPSYNC_PASSWORD1" not in os.environ, "le jeton ne doit pas passer par l'environnement"
assert os.environ["IMAPSYNC_PASSWORD2"] == "mot-de-passe"
path = sys.argv[sys.argv.index("--oauthaccesstoken1") + 1]
print("token-file-first-line=" + open(path, encoding="utf-8").readline().strip())
print("Detected 0 errors")
''', encoding="utf-8")
    from mailbox_sync.engine import command as real
    monkeypatch.setattr("mailbox_sync.runner.command",
                        lambda p, mode, files=(None, None): (sys.executable, [str(script), *real(p, mode, files)[1]]))
    runner = Runner()
    lines, results = [], []
    runner.line.connect(lines.append)
    runner.done.connect(lambda ok, message: results.append((ok, message)))
    runner.start(plan(), Mode.PREVIEW, (TOKEN, "mot-de-passe"))
    temp = runner._temp.name
    until(lambda: bool(results))
    assert results[0][0], (results, lines)
    # The engine did read the token from the file, and the log shows it masked.
    assert any("token-file-first-line=[MASQUÉ]" in line for line in lines), lines
    assert TOKEN not in "\n".join(lines)
    assert not os.path.exists(temp)              # the token file dies with the run


def test_runner_refuses_an_oauth_account_with_no_token(app, tmp_path):
    runner = Runner()
    with pytest.raises(ValueError):
        runner.start(plan(), Mode.PREVIEW, ("", "mot-de-passe"))
    assert runner._temp is None and not runner.active


def test_worker_reports_success_and_failure(app, until):
    got = []
    worker = OAuthWorker(MICROSOFT, "c", authorizer=lambda *a: Token(TOKEN, 60))
    worker.obtained.connect(lambda token, expires: got.append((token, expires)))
    worker.start()
    until(lambda: bool(got))
    worker.wait()
    assert got == [(TOKEN, 60)]
    errors = []

    def refuse(*args):
        raise OAuthError("Identifiant d'application refusé : vérifie le client_id.")
    worker = OAuthWorker(MICROSOFT, "c", "secret-client", authorizer=refuse)
    worker.failed.connect(errors.append)
    worker.start()
    until(lambda: bool(errors))
    worker.wait()
    assert "client_id" in errors[0] and "secret-client" not in errors[0]


def card_in_oauth(window, provider=MICROSOFT):
    card = window.source
    card.host.setText("outlook.example")
    card.user.setText("moi@exemple.fr")
    card.auth.setCurrentIndex(card.auth.findData(provider))
    card.client_id.setText("client-123")
    return card


def test_ui_switching_to_oauth_hides_the_password_and_shows_the_registration(app):
    window = Window()
    card = card_in_oauth(window)
    assert not card.password.isVisibleTo(card) and card.client_id.isVisibleTo(card)
    assert not card.client_secret.isVisibleTo(card)      # Microsoft needs none
    card.auth.setCurrentIndex(card.auth.findData(GOOGLE))
    assert card.client_secret.isVisibleTo(card)          # Google does
    assert window._plan().source.oauth
    assert window._plan().source.provider == GOOGLE
    card.auth.setCurrentIndex(card.auth.findData("basic"))
    assert card.password.isVisibleTo(card) and not card.client_id.isVisibleTo(card)
    assert window._plan().source.auth == "basic" and not window._plan().source.provider
    window.close()


def test_ui_token_is_dropped_when_identity_or_registration_changes(app):
    window = Window()
    card = card_in_oauth(window)
    for change in (lambda: card.user.setText("autre@exemple.fr"),
                   lambda: card.client_id.setText("client-456"),
                   lambda: card.auth.setCurrentIndex(card.auth.findData("basic"))):
        card.token = TOKEN
        card.oauth_status.setText("Compte connecté.")
        window.preview_plan = window._plan()
        window.copy.setEnabled(True)
        change()
        assert card.token == "" and card.secret() != TOKEN
        assert "non connecté" in card.oauth_status.text() or not card.token
        assert window.preview_plan is None and not window.copy.isEnabled()
    window.close()


def test_ui_secret_is_the_token_in_oauth_and_the_password_otherwise(app):
    window = Window()
    card = card_in_oauth(window)
    card.token = TOKEN
    assert card.secret() == TOKEN
    card.auth.setCurrentIndex(card.auth.findData("basic"))
    card.password.setText("mot-de-passe")
    assert card.secret() == "mot-de-passe"
    window.close()


def test_ui_closing_forgets_the_token(app):
    window = Window()
    card = card_in_oauth(window)
    card.token = TOKEN
    window.close()
    assert card.token == ""


def test_ui_connection_failure_is_shown_and_leaves_no_token(app, until, monkeypatch):
    import mailbox_sync.ui as ui

    def refuse(*args, **kwargs):
        raise OAuthError("Cette application n'est pas autorisée : active « Allow public client flows ».")
    monkeypatch.setattr(ui, "OAuthWorker",
                        lambda *a, **k: OAuthWorker(*a[:4], parent=a[4] if len(a) > 4 else None,
                                                    authorizer=refuse))
    window = Window()
    card = card_in_oauth(window)
    card.connect_button.click()
    until(lambda: card.worker is None)
    assert card.token == "" and "public client flows" in card.oauth_status.text()
    assert card.connect_button.isEnabled()
    window.close()


def test_ui_successful_connection_reports_the_validity(app, until, monkeypatch):
    import mailbox_sync.ui as ui
    monkeypatch.setattr(ui, "OAuthWorker",
                        lambda *a, **k: OAuthWorker(*a[:4], parent=a[4] if len(a) > 4 else None,
                                                    authorizer=lambda *x: Token(TOKEN, 3599)))
    window = Window()
    card = card_in_oauth(window)
    card.connect_button.click()
    until(lambda: card.worker is None)
    assert card.token == TOKEN
    assert re.search(r"59 minutes", card.oauth_status.text())
    assert "en mémoire pour cette session" in card.oauth_status.text()
    window.close()
