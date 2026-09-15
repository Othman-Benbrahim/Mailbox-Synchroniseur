from dataclasses import dataclass
import datetime
from enum import Enum
import ipaddress
import re


class Mode(str, Enum):
    LOGIN = "login"
    PREVIEW = "preview"
    COPY = "copy"


@dataclass(frozen=True)
class Account:
    host: str
    user: str
    port: int = 993
    security: str = "SSL"

    def validate(self):
        if not self.host or self.host != self.host.strip():
            raise ValueError("Renseigne un nom de serveur IMAP sans espaces.")
        try:
            ipaddress.ip_address(self.host)
        except ValueError:
            try:
                ascii_host = self.host.encode("idna").decode("ascii")
            except UnicodeError:
                raise ValueError("Nom de serveur invalide.") from None
            if len(ascii_host) > 253 or not all(
                re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", part)
                for part in ascii_host.rstrip(".").split(".")
            ):
                raise ValueError("Utilise un nom d'hôte ou une IP, sans https:// ni chemin.")
        if not self.user.strip() or self.user.startswith("-") or any(ord(c) < 32 for c in self.user):
            raise ValueError("Renseigne un identifiant IMAP valide.")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("Le port doit être compris entre 1 et 65535.")
        if self.security not in ("SSL", "STARTTLS"):
            raise ValueError("Une connexion TLS est obligatoire.")

    @property
    def network_host(self):
        return self.host.encode("idna").decode("ascii")


@dataclass(frozen=True)
class FolderMapping:
    source: str
    destination: str = ""

    def validate(self):
        if not isinstance(self.destination, str):
            raise ValueError("Nom de dossier destination invalide.")
        for name in (self.source, self.destination or self.source):
            if not isinstance(name, str) or not name.strip() or name.startswith("-") or any(ord(c) < 32 for c in name):
                raise ValueError("Renseigne des noms de dossiers valides.")
        if "=" in self.source:
            raise ValueError("Un nom de dossier source contenant = n'est pas pris en charge en sélection manuelle.")


def parse_date(value: str) -> datetime.date:
    """Strict ISO calendar date (AAAA-MM-JJ). Anything else is refused."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Renseigne les dates au format AAAA-MM-JJ.")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError("Date de filtre invalide.") from None


@dataclass(frozen=True)
class Filters:
    """Optional message selection. All fields None means no filter at all.

    Dates are ISO strings applied by the server on the IMAP internal date
    (INTERNALDATE), both bounds inclusive. Sizes are bytes of the raw message
    (RFC822.SIZE): messages strictly larger than max_size or smaller than or
    equal to min_size are skipped by the engine and counted as skipped.
    """
    since: str | None = None
    until: str | None = None
    max_size: int | None = None
    min_size: int | None = None

    def validate(self):
        since = parse_date(self.since) if self.since is not None else None
        until = parse_date(self.until) if self.until is not None else None
        if since and until and since > until:
            raise ValueError("La date de début du filtre doit précéder la date de fin.")
        for value in (self.max_size, self.min_size):
            if value is not None and (type(value) is not int or value <= 0 or value > 2**40):
                raise ValueError("Les tailles de filtre doivent être des entiers strictement positifs.")
        if self.max_size is not None and self.min_size is not None and self.max_size <= self.min_size:
            raise ValueError("La taille maximale doit dépasser la taille minimale.")

    @property
    def active(self):
        return any(value is not None for value in (self.since, self.until, self.max_size, self.min_size))

    def describe(self):
        parts = []
        if self.since and self.until:
            parts.append(f"du {self.since} au {self.until}")
        elif self.since:
            parts.append(f"depuis le {self.since}")
        elif self.until:
            parts.append(f"jusqu'au {self.until}")
        if self.max_size is not None:
            parts.append(f"taille ≤ {self.max_size // 1024} Kio")
        if self.min_size is not None:
            parts.append(f"taille > {self.min_size // 1024} Kio")
        return ", ".join(parts) if parts else "aucun filtre"


@dataclass(frozen=True)
class Plan:
    source: Account
    destination: Account
    engine: str
    folders: tuple[FolderMapping, ...] | None = None
    filters: Filters = Filters()
    mirror: bool = False          # delete at the destination what is no longer at the source
    expunge: bool = False         # empty the destination instead of only marking \Deleted

    @property
    def destructive(self):
        return bool(self.mirror)

    def validate(self):
        self.source.validate()
        self.destination.validate()
        if not isinstance(self.filters, Filters):
            raise ValueError("Filtres invalides.")
        self.filters.validate()
        if (self.source.host.rstrip(".").casefold(), self.source.port, self.source.user) == (
            self.destination.host.rstrip(".").casefold(), self.destination.port, self.destination.user
        ):
            raise ValueError("La source et la destination désignent le même compte.")
        if not self.engine.strip():
            raise ValueError("Sélectionne l'exécutable imapsync dans la configuration.")
        if type(self.mirror) is not bool or type(self.expunge) is not bool:
            raise ValueError("Option de miroir invalide.")
        if self.expunge and not self.mirror:
            raise ValueError("Le vidage de la destination n'a de sens qu'avec le miroir.")
        if self.mirror and self.filters.active:
            # A filter hides source messages from the engine; mirroring would then delete
            # perfectly legitimate messages at the destination. Refused, never silently.
            raise ValueError("Le miroir est incompatible avec un filtre : les messages exclus "
                             "par le filtre seraient supprimés à destination.")

        if self.folders is not None:
            if not isinstance(self.folders, tuple) or not self.folders:
                raise ValueError("Ajoute au moins un dossier ou sélectionne tous les dossiers.")
            sources, destinations = set(), set()
            for folder in self.folders:
                if not isinstance(folder, FolderMapping):
                    raise ValueError("Correspondance de dossiers invalide.")
                folder.validate()
                source = folder.source.casefold()
                destination = (folder.destination or folder.source).casefold()
                if source in sources or destination in destinations:
                    raise ValueError("Chaque dossier source et destination doit être unique dans la sélection.")
                sources.add(source)
                destinations.add(destination)


def validate_passwords(passwords):
    if len(passwords) != 2 or any(not p or any(c in p for c in "\r\n\0") for p in passwords):
        raise ValueError("Renseigne les deux mots de passe (sans retour à la ligne).")
