"""Local history: one JSON file per run, without any secret.

What is stored is what the report and the plan already show on screen: servers,
identifiers, scope, filters and counters. Never a password, never the session log
(which can contain folder names and engine output the user has not chosen to keep).
Files live in the user's data directory, are readable, and can be deleted one by one.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from .models import Filters, FolderMapping, Mode, Plan
from .report import MigrationReport, human_size

VERSION = 1
KEEP = 200                       # oldest entries beyond this are pruned
MAX_BYTES = 256 * 1024
NAME = re.compile(r"^\d{8}-\d{6}-\d{3}-(login|preview|copy)\.json$")


def data_directory() -> Path:
    """Per-user data directory. MAILBOX_HISTORY_DIR overrides it (tests, portable use)."""
    override = os.environ.get("MAILBOX_HISTORY_DIR")
    if override:
        return Path(override)
    try:
        from PySide6.QtCore import QStandardPaths
        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    except Exception:
        base = ""
    if not base:
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
        base = os.path.join(base, "MailboxSynchroniseur")
    return Path(base) / "historique"


@dataclass(frozen=True)
class Entry:
    """A finished run, as the bilan described it."""
    started: str                 # ISO 8601, local time with offset
    finished: str
    mode: str
    ok: bool
    message: str
    source: dict = field(default_factory=dict)        # host, user, port, security
    destination: dict = field(default_factory=dict)
    folders: list | None = None                       # [{source, destination}] or None = all
    filters: dict = field(default_factory=dict)
    counters: dict = field(default_factory=dict)
    engine_exit_code: int | None = None
    mirror: bool = False
    expunge: bool = False
    path: Path | None = None                          # set when read back; not serialised

    @property
    def label(self):
        mode = {"login": "Test des accès", "preview": "Simulation", "copy": "Copie"}.get(self.mode, self.mode)
        when = self.started.replace("T", " ")[:19]
        return f"{when} · {mode} · {'réussi' if self.ok else 'échec'}"


def account_of(account) -> dict:
    return {"host": account.host, "user": account.user, "port": account.port,
            "security": account.security}


def build(plan: Plan, report: MigrationReport, ok: bool, message: str, started: datetime,
          finished: datetime | None = None) -> Entry:
    counters = {name: getattr(report, name) for name in
                ("transferred", "plannable", "skipped", "errors", "missing", "unidentified",
                 "source_bytes", "skipped_bytes", "transferred_bytes", "size_filtered",
                 "marked_deleted", "deleted_folders")}
    counters["destination_confirmed"] = report.destination_confirmed
    counters["estimated_bytes"] = report.estimated_bytes
    return Entry(
        started=started.astimezone().isoformat(timespec="seconds"),
        finished=(finished or datetime.now(timezone.utc)).astimezone().isoformat(timespec="seconds"),
        mode=Mode(report.mode).value, ok=ok, message=message,
        source=account_of(plan.source), destination=account_of(plan.destination),
        folders=None if plan.folders is None else [asdict(f) for f in plan.folders],
        filters=asdict(plan.filters), counters=counters, engine_exit_code=report.exit_code,
        mirror=plan.mirror, expunge=plan.expunge,
    )


def save(entry: Entry, directory: Path | None = None) -> Path:
    directory = Path(directory or data_directory())
    directory.mkdir(parents=True, exist_ok=True)
    content = {k: v for k, v in asdict(entry).items() if k != "path"}
    content["version"] = VERSION
    stamp = datetime.fromisoformat(entry.started).strftime("%Y%m%d-%H%M%S")
    for suffix in range(1000):
        target = directory / f"{stamp}-{suffix:03d}-{entry.mode}.json"
        if not target.exists():
            break
    else:
        raise OSError("Trop d'entrées d'historique à la même seconde.")
    handle, temporary = tempfile.mkstemp(prefix=".mailbox-", dir=directory)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(content, out, indent=2, ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    prune(directory)
    return target


def prune(directory: Path, keep: int = KEEP):
    files = sorted(f for f in directory.glob("*.json") if NAME.match(f.name))
    for old in files[:-keep] if keep else files:
        try:
            old.unlink()
        except OSError:
            pass


def read(path: Path) -> Entry:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Entrée d'historique trop volumineuse.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != VERSION:
            raise ValueError("Version d'historique non reconnue.")
        data.pop("version")
        return Entry(path=path, **data)
    except (TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Entrée d'historique illisible : {path.name}.") from exc


def load(directory: Path | None = None) -> tuple[Entry, ...]:
    """Most recent first. A corrupted file is skipped, not fatal."""
    directory = Path(directory or data_directory())
    if not directory.is_dir():
        return ()
    entries = []
    for path in sorted(directory.glob("*.json"), reverse=True):
        if not NAME.match(path.name):
            continue
        try:
            entries.append(read(path))
        except (OSError, ValueError):
            continue
    return tuple(entries)


def _number(value):
    return "non communiqué" if value is None else str(value)


def _size(value):
    return "non communiqué" if value is None else human_size(value)


def report_text(entry: Entry) -> str:
    """Plain-text report for export. Contains no password; servers, identifiers and
    folder names are included, as they are in the profile and on screen."""
    counters = entry.counters
    filters = Filters(**entry.filters) if entry.filters else Filters()
    lines = [
        "Mailbox Synchroniseur — rapport d'opération",
        "",
        f"Début   : {entry.started}",
        f"Fin     : {entry.finished}",
        f"Mode    : {entry.label.split(' · ')[1]}",
        f"Résultat: {'réussi' if entry.ok else 'échec'} — {entry.message}",
        f"Code de sortie du moteur : {_number(entry.engine_exit_code)}",
        "",
        f"Source      : {entry.source.get('user')} sur {entry.source.get('host')}:"
        f"{entry.source.get('port')} ({entry.source.get('security')})",
        f"Destination : {entry.destination.get('user')} sur {entry.destination.get('host')}:"
        f"{entry.destination.get('port')} ({entry.destination.get('security')})",
        "",
        f"Filtres : {filters.describe()}",
        ("Miroir : actif — suppressions à destination"
         + (", vidage définitif" if entry.expunge else ", marquage « supprimé » seulement")
         if entry.mirror else "Miroir : inactif — aucune suppression"),
    ]
    if entry.folders is None:
        lines.append("Périmètre : tous les dossiers")
    else:
        lines.append(f"Périmètre : {len(entry.folders)} dossier(s) sélectionné(s)")
        for mapping in entry.folders:
            target = mapping.get("destination") or mapping.get("source")
            lines.append(f"  - {mapping.get('source')} → {target}")
    lines += [
        "",
        f"Copiés              : {_number(counters.get('transferred'))}",
        f"À copier (simulation): {_number(counters.get('plannable'))}",
        f"Ignorés             : {_number(counters.get('skipped'))}",
        f"Erreurs             : {_number(counters.get('errors'))}",
        f"Absents à destination: {_number(counters.get('missing'))}",
        f"Exclus par le filtre de taille : {_number(counters.get('size_filtered'))}",
        f"Supprimés à destination : {_number(counters.get('marked_deleted'))}",
        f"Volume transféré    : {_size(counters.get('transferred_bytes'))}",
        f"Volume estimé       : {_size(counters.get('estimated_bytes'))}",
        "",
        ("Présence des messages identifiés confirmée par imapsync."
         if counters.get("destination_confirmed") else
         "Présence complète à destination non confirmée."),
        "",
        "Ce rapport ne contient aucun mot de passe et ne reprend pas le journal de session.",
    ]
    return "\n".join(lines) + "\n"


def export(entry: Entry, path: Path) -> Path:
    path = Path(path)
    path.write_text(report_text(entry), encoding="utf-8")
    return path


def delete(entry: Entry):
    if entry.path is not None:
        entry.path.unlink(missing_ok=True)


def delete_all(directory: Path | None = None) -> int:
    directory = Path(directory or data_directory())
    removed = 0
    if directory.is_dir():
        for path in directory.glob("*.json"):
            if NAME.match(path.name):
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    pass
    return removed


def mappings_of(entry: Entry):
    """Folder selection of a past run, to reuse it. Filters come back as a Filters."""
    if entry.folders is None:
        return None
    return tuple(FolderMapping(**item) for item in entry.folders)
