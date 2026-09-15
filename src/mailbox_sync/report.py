"""Observations from imapsync 2.314. Absent counters are not invented.

Lines parsed here are printed by the engine's final statistics block and by
its folder-sizes listing. Their exact wording was read in the pinned imapsync
source (commit 93654c6) and is exercised against the real engine in
tests/integration; a change of wording yields "non communiqué", never a number.
"""
from dataclasses import dataclass
import re
from .models import Mode


def human_size(value: int) -> str:
    if value < 1024:
        return f"{value} octets"
    size = value / 1024
    for unit in ("Kio", "Mio", "Gio"):
        if size < 1024:
            break
        size /= 1024
    else:
        unit = "Tio"
    return f"{size:.1f} {unit}".replace(".", ",")


@dataclass
class MigrationReport:
    mode: Mode = Mode.LOGIN
    transferred: int | None = None
    plannable: int | None = None      # "(could be N without --dry mode)": what a copy would transfer
    skipped: int | None = None
    errors: int | None = None
    missing: int | None = None
    unidentified: int | None = None
    source_bytes: int | None = None   # "Host1 Total size": selected messages in the chosen folders
    skipped_bytes: int | None = None  # "Total bytes skipped": already present, size-filtered or unreadable
    transferred_bytes: int | None = None
    size_filtered: int = 0            # "msg F/UID skipped (N exceeds maxsize…)" lines, copy only
    size_filter: bool = False         # the plan carries a size filter; set by the caller
    mirror: bool = False              # the plan mirrors; set by the caller
    marked_deleted: int = 0           # "Host2: msg F/UID marked \Deleted on host2" lines
    deleted_folders: int | None = None
    expunged: bool = False            # the plan asked to empty, not only to mark
    exit_code: int | None = None
    cancelled: bool = False
    crashed: bool = False

    def feed(self, line: str):
        # The engine ends its lines with LF on Linux and CRLF on Windows; the
        # runner hands them over unstripped so that they are matched identically.
        line = line.rstrip("\r\n")
        for label, attribute in (("Messages transferred", "transferred"),
                                 ("Messages skipped", "skipped"),
                                 ("Messages found in host1 not in host2", "missing"),
                                 ("Total bytes transferred", "transferred_bytes"),
                                 ("Total bytes skipped", "skipped_bytes"),
                                 ("Host1 Total size", "source_bytes")):
            match = re.match(r"^" + re.escape(label) + r"\s*:\s*(\d+)\b", line)
            if match:
                setattr(self, attribute, int(match[1]))
        match = re.match(r"^Messages transferred\s*:\s*\d+\s*\(could be (\d+) without --dry mode\)", line)
        if match:
            self.plannable = int(match[1])
        match = re.match(r"^Detected (\d+) errors\b", line)
        if match:
            self.errors = int(match[1])
        if re.match(r"^msg .+ skipped \(\d+ (?:exceeds maxsize limit|smaller than minsize) \d+ bytes\)$", line):
            self.size_filtered += 1
        # Printed once per message the engine marks \Deleted at the destination, in dry
        # mode too (followed there by "(not really since --dry mode)").
        if re.match(r"^Host2: msg .+ marked \\Deleted", line):
            self.marked_deleted += 1
        match = re.match(r"^Folders deleted on host2\s*:\s*(\d+)\b", line)
        if match:
            self.deleted_folders = int(match[1])
        if line.startswith("There is no unidentified message on host1."):
            self.unidentified = 0
        match = re.match(r"^There are (\d+) unidentified messages", line)
        if match:
            self.unidentified = int(match[1])

    @property
    def unexplained_missing(self):
        """Messages the engine identified on the source but not on the destination,
        minus those it reported skipping because of the size filter. imapsync
        identifies every selected source message before applying --maxsize/--minsize,
        so a deliberately excluded message is still listed as "found in host1 not in
        host2"; it is accounted for here, never hidden."""
        if self.missing is None:
            return None
        return self.missing - self.size_filtered

    @property
    def destination_confirmed(self):
        return (self.mode == Mode.COPY and self.exit_code == 0 and
                not self.cancelled and not self.crashed and self.errors == 0 and
                self.unexplained_missing == 0 and self.unidentified == 0)

    @property
    def estimated_bytes(self):
        """Bytes a copy would transfer, derived from a simulation.

        imapsync does not sum the size of the messages it would copy in --dry
        mode. It does report the size of every selected source message (Host1
        Total size) and the size of every message it skipped (Total bytes
        skipped); the difference is what remains to copy. Only for a simulation
        that ended with exit code 0 and zero errors, and never negative.
        """
        if (self.mode != Mode.PREVIEW or self.exit_code != 0 or self.errors != 0
                or self.source_bytes is None or self.skipped_bytes is None):
            return None
        estimate = self.source_bytes - self.skipped_bytes
        return estimate if estimate >= 0 else None

    @property
    def deletion_summary(self):
        """What a mirror run announces or has done at the destination."""
        if not self.mirror:
            return ""
        if self.mode == Mode.PREVIEW:
            return (f"\nSuppressions annoncées à destination : {self.marked_deleted} message(s). "
                    "Aucune suppression n'a eu lieu pendant la simulation.")
        return (f"\nSupprimés à destination : {self.marked_deleted} message(s) marqués « supprimé »"
                + (" et définitivement retirés." if self.expunged else
                   " ; ils restent récupérables tant que la boîte n'est pas vidée."))

    def text(self):
        def number(value):
            return str(value) if value is not None else "non communiqué"

        def size(value):
            return human_size(value) if value is not None else "non communiqué"
        if self.mode == Mode.LOGIN:
            return "Test des accès : aucun transfert demandé."
        if self.mode == Mode.PREVIEW:
            caveat = (" · avant filtre de taille, appliqué seulement lors de la copie"
                      if self.size_filter else "")
            return (f"Simulation — À copier : {number(self.plannable)} · Ignorés : {number(self.skipped)} · "
                    f"Erreurs : {number(self.errors)} · Absents à destination : {number(self.missing)}\n"
                    f"Volume estimé à copier : {size(self.estimated_bytes)}"
                    f" (source sélectionnée : {size(self.source_bytes)} · ignoré : {size(self.skipped_bytes)}{caveat})"
                    + self.deletion_summary)
        missing = number(self.missing)
        if self.size_filtered:
            missing += f" (dont {self.size_filtered} exclus par le filtre de taille)"
        return (f"Copiés : {number(self.transferred)} · Ignorés : {number(self.skipped)} · "
                f"Erreurs : {number(self.errors)} · Absents à destination : {missing}\n"
                f"Volume transféré : {size(self.transferred_bytes)}\n"
                + self.deletion_summary.lstrip("\n") + ("\n" if self.mirror else "")
                + ("Présence des messages identifiés confirmée par imapsync"
                   + (", hors messages exclus par le filtre de taille." if self.size_filtered else ".")
                   if self.destination_confirmed else "Présence complète à destination non confirmée."))
