"""Observations from imapsync 2.314. Absent counters are not invented."""
from dataclasses import dataclass
import re
from .models import Mode


@dataclass
class MigrationReport:
    mode: Mode = Mode.LOGIN
    transferred: int | None = None
    skipped: int | None = None
    errors: int | None = None
    missing: int | None = None
    unidentified: int | None = None
    exit_code: int | None = None
    cancelled: bool = False
    crashed: bool = False

    def feed(self, line: str):
        for label, attribute in (("Messages transferred", "transferred"),
                                 ("Messages skipped", "skipped"),
                                 ("Messages found in host1 not in host2", "missing")):
            match = re.match(r"^" + re.escape(label) + r"\s*:\s*(\d+)\b", line)
            if match:
                setattr(self, attribute, int(match[1]))
        match = re.match(r"^Detected (\d+) errors\b", line)
        if match:
            self.errors = int(match[1])
        if line.startswith("There is no unidentified message on host1."):
            self.unidentified = 0
        match = re.match(r"^There are (\d+) unidentified messages", line)
        if match:
            self.unidentified = int(match[1])

    @property
    def destination_confirmed(self):
        return (self.mode == Mode.COPY and self.exit_code == 0 and
                not self.cancelled and not self.crashed and self.errors == 0 and
                self.missing == 0 and self.unidentified == 0)

    def text(self):
        def number(value):
            return str(value) if value is not None else "non communiqué"
        if self.mode == Mode.LOGIN:
            return "Test des accès : aucun transfert demandé."
        prefix = "Simulation — " if self.mode == Mode.PREVIEW else ""
        counts = (f"{prefix}Copiés : {number(self.transferred)} · Ignorés : {number(self.skipped)} · "
                  f"Erreurs : {number(self.errors)} · Absents à destination : {number(self.missing)}")
        if self.mode == Mode.COPY:
            counts += "\n" + ("Présence des messages identifiés confirmée par imapsync."
                               if self.destination_confirmed else "Présence complète à destination non confirmée.")
        return counts
