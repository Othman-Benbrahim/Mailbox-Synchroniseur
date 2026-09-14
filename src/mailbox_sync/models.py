from dataclasses import dataclass
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


@dataclass(frozen=True)
class Plan:
    source: Account
    destination: Account
    engine: str
    folders: tuple[FolderMapping, ...] | None = None

    def validate(self):
        self.source.validate()
        self.destination.validate()
        if (self.source.host.rstrip(".").casefold(), self.source.port, self.source.user) == (
            self.destination.host.rstrip(".").casefold(), self.destination.port, self.destination.user
        ):
            raise ValueError("La source et la destination désignent le même compte.")
        if not self.engine.strip():
            raise ValueError("Sélectionne l'exécutable imapsync dans la configuration.")

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
