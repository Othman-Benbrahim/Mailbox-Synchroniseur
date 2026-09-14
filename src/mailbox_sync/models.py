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
class Plan:
    source: Account
    destination: Account
    engine: str

    def validate(self):
        self.source.validate()
        self.destination.validate()
        if (self.source.host.rstrip(".").casefold(), self.source.port, self.source.user) == (
            self.destination.host.rstrip(".").casefold(), self.destination.port, self.destination.user
        ):
            raise ValueError("La source et la destination désignent le même compte.")
        if not self.engine.strip():
            raise ValueError("Sélectionne l'exécutable imapsync dans la configuration.")


def validate_passwords(passwords):
    if len(passwords) != 2 or any(not p or any(c in p for c in "\r\n\0") for p in passwords):
        raise ValueError("Renseigne les deux mots de passe (sans retour à la ligne).")
