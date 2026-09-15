"""Pure proposal of a folder mapping. Nothing here talks to a server.

The proposal is a suggestion the user reviews in the folder table; the
simulation gate still applies before any copy.
"""
from dataclasses import dataclass
from .discovery import Folder
from .models import FolderMapping

# Names commonly used by providers for each role, compared case-insensitively.
ALIASES = {
    "sent": ("sent", "sent items", "sent messages", "sent mail", "envoyés", "envoyes",
             "éléments envoyés", "elements envoyes", "messages envoyés", "messages envoyes",
             "[gmail]/sent mail", "[google mail]/sent mail"),
    "drafts": ("drafts", "draft", "brouillons", "[gmail]/drafts", "[google mail]/drafts"),
    "trash": ("trash", "deleted items", "deleted messages", "corbeille", "éléments supprimés",
              "elements supprimes", "bin", "[gmail]/trash", "[gmail]/bin", "[google mail]/trash"),
    "junk": ("junk", "junk e-mail", "junk email", "spam", "pourriel", "pourriels",
             "courrier indésirable", "courrier indesirable", "indésirables", "indesirables",
             "[gmail]/spam", "[google mail]/spam"),
    "archive": ("archive", "archives", "archived"),
}
ROLE_LABEL = {"sent": "messages envoyés", "drafts": "brouillons", "trash": "corbeille",
              "junk": "indésirables", "archive": "archives"}


@dataclass(frozen=True)
class Proposal:
    mapping: FolderMapping | None   # None when the folder is excluded from the proposal
    source: str
    kind: str                       # identique | rôle | casse | séparateur | nouveau | exclu
    reason: str


def role_of(folder: Folder) -> str | None:
    if folder.role:
        return folder.role
    lowered = folder.name.casefold()
    for role, names in ALIASES.items():
        if lowered in names:
            return role
    return None


def translate(name: str, source_delimiter: str | None, destination_delimiter: str | None) -> str:
    if not source_delimiter or not destination_delimiter or source_delimiter == destination_delimiter:
        return name
    return name.replace(source_delimiter, destination_delimiter)


def propose(source: tuple[Folder, ...], destination: tuple[Folder, ...]) -> tuple[Proposal, ...]:
    by_name = {f.name: f for f in destination}
    by_casefold = {}
    for f in destination:
        by_casefold.setdefault(f.name.casefold(), f)
    by_role = {}
    for f in destination:
        role = role_of(f)
        if role and f.selectable:
            by_role.setdefault(role, f)
    used, results = set(), []
    # Parents first so that children can inherit a renamed prefix; otherwise the
    # server's order is kept, so the first of two candidates for one role wins.
    ordered = sorted(source, key=lambda f: f.name.count(f.delimiter) if f.delimiter else 0)
    renamed = {}   # source name -> destination name, for prefix inheritance

    def inherited(folder):
        if not folder.delimiter:
            return None
        parts = folder.name.split(folder.delimiter)
        for cut in range(len(parts) - 1, 0, -1):
            prefix = folder.delimiter.join(parts[:cut])
            if prefix in renamed and renamed[prefix] != prefix:
                target = renamed[prefix]
                rest = parts[cut:]
                dest_delimiter = target_delimiter(target)
                return target + dest_delimiter + dest_delimiter.join(rest)
        return None

    def target_delimiter(target_name):
        target = by_name.get(target_name)
        if target and target.delimiter:
            return target.delimiter
        return next((f.delimiter for f in destination if f.delimiter), None) or "/"

    for folder in ordered:
        if not folder.selectable:
            results.append(Proposal(None, folder.name, "exclu", "non sélectionnable sur la source"))
            continue
        if folder.role == "all":
            results.append(Proposal(None, folder.name, "exclu",
                                    "dossier « tous les messages » : les copier dupliquerait chaque dossier"))
            continue
        role = role_of(folder)
        candidate = kind = reason = None
        if folder.name == "INBOX" or folder.name in by_name:
            candidate, kind, reason = folder.name, "identique", "même nom à destination"
        elif role and role in by_role:
            candidate, kind = by_role[role].name, "rôle"
            reason = f"{ROLE_LABEL[role]} : « {folder.name} » correspond à « {candidate} »"
        elif folder.name.casefold() in by_casefold:
            candidate, kind = by_casefold[folder.name.casefold()].name, "casse"
            reason = "même nom à la casse près"
        else:
            parent = inherited(folder)
            if parent:
                candidate, kind, reason = parent, "séparateur", "sous-dossier d'un dossier renommé"
            else:
                dest_delimiter = target_delimiter(folder.name)
                translated = translate(folder.name, folder.delimiter, dest_delimiter)
                if translated in by_name:
                    candidate, kind, reason = translated, "séparateur", "même nom avec le séparateur de la destination"
                else:
                    candidate, kind = translated, "nouveau"
                    reason = ("sera créé à destination" if translated == folder.name
                              else "sera créé à destination, séparateur adapté")
        if candidate.casefold() in used:
            results.append(Proposal(None, folder.name, "exclu",
                                    f"« {candidate} » est déjà la destination d'un autre dossier ; à régler manuellement"))
            continue
        used.add(candidate.casefold())
        renamed[folder.name] = candidate
        results.append(Proposal(FolderMapping(folder.name, "" if candidate == folder.name else candidate),
                                folder.name, kind, reason))
    return tuple(results)


def describe(proposals: tuple[Proposal, ...]) -> str:
    lines = []
    for p in proposals:
        if p.mapping is None:
            lines.append(f"✗ {p.source} — exclu : {p.reason}")
        else:
            target = p.mapping.destination or p.mapping.source
            arrow = "=" if not p.mapping.destination else "→"
            lines.append(f"• {p.source} {arrow} {target} — {p.reason}")
    return "\n".join(lines) if lines else "Aucun dossier trouvé sur la source."
