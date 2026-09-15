"""Phase 3, lot 3b: folder discovery (LIST parsing) and mapping proposal. No real IMAP here."""
import ssl
import pytest
from mailbox_sync.discovery import DiscoveryError, Folder, list_folders, parse_list_response
from mailbox_sync.discovery_worker import DiscoveryWorker
from mailbox_sync.folders import imap_utf7, imap_utf7_decode
from mailbox_sync.mapping import describe, propose, role_of
from mailbox_sync.models import Account, FolderMapping
from mailbox_sync.ui import Window


@pytest.mark.parametrize("name", ["INBOX", "A&B", "Été", "日本語", "Archives/Été & 日本語", "&-", "x&zz", "Envoy&AOk-s"])
def test_utf7_roundtrip(name):
    assert imap_utf7_decode(imap_utf7(name)) == name


def test_utf7_decode_tolerates_invalid_sections():
    assert imap_utf7_decode("&AOk") == "&AOk"
    assert imap_utf7_decode("a&!!-b") == "a&!!-b"


def test_parse_list_from_several_servers():
    items = [
        b'(\\HasNoChildren) "." "INBOX"',                         # Dovecot
        b'(\\HasNoChildren \\Sent) "." "Sent"',                    # Dovecot with SPECIAL-USE
        b'(\\HasNoChildren) "/" "Sent Items"',                     # Exchange
        b'(\\HasChildren \\Noselect) "/" "[Gmail]"',               # Gmail container
        b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"',
        b'(\\HasNoChildren) "/" Archives/&AMk-t&AOk-',             # atom name, UTF-7
        b'(\\HasNoChildren) "/" "Quote \\"here\\" \\\\ back"',     # escaped quoted string
        b'(\\HasNoChildren) NIL "Flat"',                          # no hierarchy
        (b'(\\HasNoChildren) "/" {11}', b'Litt&AOk-ral'),          # literal name
        None, b'garbage',
    ]
    folders = parse_list_response(items)
    names = [f.name for f in folders]
    assert names == ["INBOX", "Sent", "Sent Items", "[Gmail]", "[Gmail]/All Mail", "Archives/Été",
                     'Quote "here" \\ back', "Flat", "Littéral"]
    assert folders[1].role == "sent" and folders[1].delimiter == "."
    assert not folders[3].selectable and folders[4].role == "all"
    assert folders[5].raw == "Archives/&AMk-t&AOk-"
    assert folders[7].delimiter is None
    assert folders[8].raw == "Litt&AOk-ral"


def F(name, delimiter="/", *attrs):
    return Folder(name, imap_utf7(name), delimiter, frozenset(a.lower() for a in attrs))


def mapped(proposals):
    return {p.source: (p.mapping, p.kind) for p in proposals}


def test_role_by_attribute_then_alias():
    assert role_of(F("Whatever", "/", "\\Sent")) == "sent"
    assert role_of(F("Éléments envoyés")) == "sent"
    assert role_of(F("[Gmail]/Spam")) == "junk"
    assert role_of(F("Projets")) is None


def test_proposal_identical_role_case_delimiter_new_and_exclusions():
    source = (F("INBOX", "."), F("Envoyés", "."), F("Brouillons", "."), F("projets", "."),
              F("Archives.2020", "."), F("Archives", "."), F("Tout", ".", "\\All"),
              F("Conteneur", ".", "\\Noselect"), F("Corbeille", "."))
    destination = (F("INBOX"), F("Sent Items"), F("Drafts", "/", "\\Drafts"), F("Projets"),
                   F("Deleted Items"))
    proposals = propose(source, destination)
    m = mapped(proposals)
    assert m["INBOX"] == (FolderMapping("INBOX", ""), "identique")
    assert m["Envoyés"] == (FolderMapping("Envoyés", "Sent Items"), "rôle")
    assert m["Brouillons"] == (FolderMapping("Brouillons", "Drafts"), "rôle")
    assert m["projets"] == (FolderMapping("projets", "Projets"), "casse")
    assert m["Archives"] == (FolderMapping("Archives", ""), "nouveau")
    assert m["Archives.2020"] == (FolderMapping("Archives.2020", "Archives/2020"), "nouveau")
    assert m["Corbeille"] == (FolderMapping("Corbeille", "Deleted Items"), "rôle")
    assert m["Tout"] == (None, "exclu") and m["Conteneur"] == (None, "exclu")
    # Every proposal is a valid, collision-free selection for a Plan.
    from mailbox_sync.models import Plan
    import sys
    Plan(Account("a.example", "u"), Account("b.example", "v"), sys.executable,
         tuple(p.mapping for p in proposals if p.mapping)).validate()


def test_children_follow_a_renamed_parent_and_conflicts_are_excluded_not_hidden():
    source = (F("Sent"), F("Sent/2019"), F("Sent/2019/Q1"), F("Envoyés"))
    destination = (F("Sent Items", "."),)
    m = mapped(propose(source, destination))
    assert m["Sent"] == (FolderMapping("Sent", "Sent Items"), "rôle")
    assert m["Sent/2019"] == (FolderMapping("Sent/2019", "Sent Items.2019"), "séparateur")
    assert m["Sent/2019/Q1"] == (FolderMapping("Sent/2019/Q1", "Sent Items.2019.Q1"), "séparateur")
    assert m["Envoyés"][0] is None and "déjà la destination" in [
        p.reason for p in propose(source, destination) if p.source == "Envoyés"][0]


def test_same_delimiter_keeps_names_and_describe_lists_everything():
    proposals = propose((F("INBOX"), F("Projets/2024"), F("X", "/", "\\Noselect")), (F("INBOX"),))
    text = describe(proposals)
    assert "• INBOX = INBOX" in text and "• Projets/2024 = Projets/2024" in text and "✗ X" in text
    assert describe(()) == "Aucun dossier trouvé sur la source."


def test_list_folders_refuses_empty_password_and_never_talks_in_clear(monkeypatch):
    with pytest.raises(DiscoveryError):
        list_folders(Account("imap.example", "u"), "")
    calls = []

    class Refuse:
        def __init__(self, *args, **kwargs):
            calls.append(kwargs)
            raise ssl.SSLCertVerificationError(1, "certificate verify failed")
    monkeypatch.setattr("mailbox_sync.discovery.imaplib.IMAP4_SSL", Refuse)
    with pytest.raises(DiscoveryError) as info:
        list_folders(Account("imap.example", "u"), "secret-value")
    assert "secret-value" not in str(info.value)
    assert calls[0]["ssl_context"].check_hostname and calls[0]["ssl_context"].verify_mode == ssl.CERT_REQUIRED


def fake_lister(folders_by_host):
    def lister(account, password):
        assert password
        if account.host == "fail.example":
            raise DiscoveryError("Authentification refusée pour u sur fail.example.")
        return folders_by_host[account.host]
    return lister


def test_worker_emits_proposal_and_drops_passwords(app, until):
    worker = DiscoveryWorker(Account("s.example", "u"), Account("d.example", "v"), ("p1", "p2"),
                             lister=fake_lister({"s.example": (F("Envoyés"),), "d.example": (F("Sent Items"),)}))
    results = []
    worker.proposed.connect(results.append)
    worker.start()
    until(lambda: bool(results))
    worker.wait()
    assert results[0][0].mapping == FolderMapping("Envoyés", "Sent Items")
    assert worker._passwords == ()


def test_worker_reports_failure_without_secret(app, until):
    worker = DiscoveryWorker(Account("fail.example", "u"), Account("d.example", "v"), ("p1", "p2"),
                             lister=fake_lister({}))
    errors = []
    worker.failed.connect(errors.append)
    worker.start()
    until(lambda: bool(errors))
    worker.wait()
    assert "refusée" in errors[0] and "p1" not in errors[0]


def fill(window, host="s.example"):
    window.source.set_account(Account(host, "u"))
    window.destination.set_account(Account("d.example", "v"))
    window.source.password.setText("p1")
    window.destination.password.setText("p2")


def test_ui_discovery_fills_table_invalidates_and_restores(app, until, monkeypatch):
    import mailbox_sync.ui as ui
    lister = fake_lister({"s.example": (F("INBOX"), F("Envoyés"), F("Tout", "/", "\\All")),
                          "d.example": (F("INBOX"), F("Sent Items"))})
    monkeypatch.setattr(ui, "DiscoveryWorker",
                        lambda s, d, p, parent: DiscoveryWorker(s, d, p, parent, lister=lister))
    window = Window()
    fill(window)
    window.preview_plan = window._plan()
    window.copy.setEnabled(True)
    window.folders.discover_button.click()
    assert not window.config.isEnabled()
    until(lambda: window.discovery is None)
    assert window.config.isEnabled() and window.preview.isEnabled()
    assert window.folders.enabled.isChecked()
    assert window.folders.value() == (FolderMapping("INBOX", ""), FolderMapping("Envoyés", "Sent Items"))
    assert "✗ Tout" in window.folders.explanations.toPlainText()
    assert window.preview_plan is None and not window.copy.isEnabled()
    assert "2 dossier(s) à copier, 1 exclu(s)" in window.status.text()
    window.close()


def test_ui_discovery_failure_restores_controls(app, until, monkeypatch):
    import mailbox_sync.ui as ui
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(ui, "DiscoveryWorker",
                        lambda s, d, p, parent: DiscoveryWorker(s, d, p, parent, lister=fake_lister({})))
    window = Window()
    fill(window, host="fail.example")
    window.folders.discover_button.click()
    until(lambda: window.discovery is None)
    assert window.config.isEnabled() and "refusée" in window.status.text()
    assert window.folders.value() is None
    window.close()


def test_ui_discovery_requires_passwords(app, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    window = Window()
    fill(window)
    window.destination.password.clear()
    window.folders.discover_button.click()
    assert window.discovery is None and "mots de passe" in window.status.text()
    window.close()
