"""Read-only folder discovery: one IMAP LIST per account, over verified TLS.

This is deliberately not a transfer engine. The application still delegates
every copy to imapsync; it only needs the folder names to propose a mapping
that the user then reviews. Nothing is created, selected or modified here.
"""
from dataclasses import dataclass
import imaplib
import re
import ssl
from .folders import imap_utf7_decode
from .models import Account

SPECIAL_USE = {"\\sent": "sent", "\\drafts": "drafts", "\\trash": "trash",
               "\\junk": "junk", "\\archive": "archive", "\\all": "all"}


@dataclass(frozen=True)
class Folder:
    name: str                  # decoded, as the user reads it
    raw: str                   # modified UTF-7 as the server lists it
    delimiter: str | None      # hierarchy delimiter, None when the server reports NIL
    attributes: frozenset      # lower-cased LIST attributes, e.g. {"\\hasnochildren", "\\sent"}

    @property
    def selectable(self):
        return "\\noselect" not in self.attributes and "\\nonexistent" not in self.attributes

    @property
    def role(self):
        for attribute, role in SPECIAL_USE.items():
            if attribute in self.attributes:
                return role
        return None


_LINE = re.compile(rb'^\((?P<attrs>[^)]*)\)\s+(?P<delim>"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.*)$', re.DOTALL)


def _unquote(value: bytes) -> str:
    if len(value) >= 2 and value[:1] == b'"' and value[-1:] == b'"':
        value = re.sub(rb"\\(.)", rb"\1", value[1:-1])
    return value.decode("utf-8", "surrogateescape")


def parse_list_response(items) -> tuple[Folder, ...]:
    """Parse imaplib's LIST payload: bytes lines, or (line, literal) tuples for
    servers that send the mailbox name as a literal."""
    folders = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, tuple):
            line, literal = item[0], item[1]
            match = _LINE.match(line)
            if not match:
                continue
            raw = literal.decode("utf-8", "surrogateescape")
        else:
            match = _LINE.match(item)
            if not match:
                continue
            raw = _unquote(match["name"].strip())
        delimiter = None if match["delim"] == b"NIL" else _unquote(match["delim"])
        attributes = frozenset(a.decode("ascii", "replace").lower() for a in match["attrs"].split())
        folders.append(Folder(imap_utf7_decode(raw), raw, delimiter or None, attributes))
    return tuple(folders)


class DiscoveryError(Exception):
    """Human-readable failure; never contains the password."""


def list_folders(account: Account, password: str, timeout: float = 30) -> tuple[Folder, ...]:
    account.validate()
    if not password:
        raise DiscoveryError("Renseigne le mot de passe avant de découvrir les dossiers.")
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    host = account.network_host
    client = None
    try:
        try:
            if account.security == "SSL":
                client = imaplib.IMAP4_SSL(host, account.port, timeout=timeout, ssl_context=context)
            else:
                client = imaplib.IMAP4(host, account.port, timeout=timeout)
                client.starttls(context)   # refused by the library if the server lacks STARTTLS
        except ssl.SSLCertVerificationError as exc:
            raise DiscoveryError(f"Certificat refusé pour {account.host} : "
                                 f"{getattr(exc, 'verify_message', None) or exc}.") from None
        except (OSError, imaplib.IMAP4.error) as exc:
            raise DiscoveryError(f"Connexion TLS impossible à {account.host}:{account.port} ({exc}).") from None
        try:
            client.login(account.user, password)
        except imaplib.IMAP4.error:
            raise DiscoveryError(f"Authentification refusée pour {account.user} sur {account.host}.") from None
        status, items = client.list()
        if status != "OK":
            raise DiscoveryError(f"Le serveur {account.host} a refusé la commande LIST.")
        return parse_list_response(items)
    except (OSError, imaplib.IMAP4.error) as exc:
        raise DiscoveryError(f"Échec de la découverte sur {account.host} ({exc}).") from None
    finally:
        if client is not None:
            try:
                client.logout()
            except (OSError, imaplib.IMAP4.error):
                pass
