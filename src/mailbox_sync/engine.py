"""Pure command construction. No arbitrary command-line options are accepted."""
from pathlib import Path
import base64
import datetime
import re
from urllib.parse import quote
from .models import Filters, Mode, Plan, parse_date
from .folders import imap_utf7

# RFC 3501 date-month is always English, whatever the process locale.
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def imap_date(value: datetime.date) -> str:
    return f"{value.day}-{MONTHS[value.month - 1]}-{value.year}"


def search_criteria(filters: Filters) -> str | None:
    """IMAP SEARCH criteria applied by the server on INTERNALDATE, both bounds inclusive.

    SINCE d selects messages dated d or later; BEFORE d selects messages dated
    strictly before d, so the inclusive end date is shifted by one day.
    """
    parts = []
    if filters.since is not None:
        parts.append(f"SINCE {imap_date(parse_date(filters.since))}")
    if filters.until is not None:
        parts.append(f"BEFORE {imap_date(parse_date(filters.until) + datetime.timedelta(days=1))}")
    return " ".join(parts) or None


def command(plan: Plan, mode: Mode) -> tuple[str, list[str]]:
    plan.validate()
    mode = Mode(mode)
    engine = Path(plan.engine).expanduser().resolve()
    if not engine.is_file():
        raise ValueError("Exécutable imapsync introuvable. Sélectionne son fichier.")
    # Never --delete1: the source is never touched, in any mode.
    args = ["--noreleasecheck", "--nolog", "--noexpunge1", "--nodelete1",
            "--noresyncflags", "--regexflag", r"s/\\Deleted//g"]
    mirror = plan.mirror and mode != Mode.LOGIN
    if mirror:
        args += ["--delete2"]
        # --delete2 turns on uidexpunge2 (or expunge2) by itself. Marking \Deleted without
        # emptying is the default here, so the user can still recover the messages.
        args += ["--expunge2", "--nouidexpunge2"] if plan.expunge else ["--noexpunge2", "--nouidexpunge2"]
    else:
        args += ["--noexpunge2"]
    for index, account in enumerate((plan.source, plan.destination), 1):
        args += [f"--host{index}", account.network_host, f"--user{index}", account.user,
                 f"--port{index}", str(account.port)]
        args += ([f"--ssl{index}", f"--notls{index}"] if account.security == "SSL"
                 else [f"--nossl{index}", f"--tls{index}"])
        for option in ("SSL_verify_mode=1", "SSL_verifycn_scheme=imap",
                       f"SSL_verifycn_name={account.network_host}"):
            args += [f"--sslargs{index}", option]
        args += [f"--timeout{index}", "30"]
    if mode == Mode.LOGIN:
        args += ["--justlogin"]
    elif mode == Mode.PREVIEW:
        args += ["--dry"]
    if mode != Mode.LOGIN:
        if plan.folders is not None:
            for folder in plan.folders:
                source = imap_utf7(folder.source)
                destination = imap_utf7(folder.destination or folder.source)
                args += ["--folder", source, "--f1f2", f"{source}={destination}"]
        criteria = search_criteria(plan.filters)
        if criteria:
            args += ["--search", criteria]
        if plan.filters.max_size is not None:
            args += ["--maxsize", str(plan.filters.max_size)]
        if plan.filters.min_size is not None:
            args += ["--minsize", str(plan.filters.min_size)]
    return str(engine), args


class Redactor:
    def __init__(self, passwords=()):
        values = set()
        for secret in passwords:
            if secret:
                values.update((secret, quote(secret, safe=""),
                               base64.b64encode(secret.encode()).decode()))
        self.values = sorted(values, key=len, reverse=True)

    def clean(self, line):
        # Drop escape controls; leave tabs intact. Match complete lines after buffering.
        line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line)
        for value in self.values:
            line = line.replace(value, "[MASQUÉ]")
        return "".join(c for c in line if c == "\t" or ord(c) >= 32)


def outcome(code: int) -> str:
    return {
        0: "Opération terminée sans erreur signalée par imapsync.",
        12: "Connexion TLS refusée : vérifie le certificat et le nom du serveur.",
        16: "Authentification refusée : vérifie les accès et les exigences du fournisseur.",
        161: "Authentification refusée sur le compte source.",
        162: "Authentification refusée sur le compte destination.",
        101: "Impossible de joindre le serveur source.",
        102: "Impossible de joindre le serveur destination.",
        113: "Quota de la destination atteint ; la copie peut être partielle.",
        121: "La recherche IMAP a échoué : vérifie que les serveurs acceptent le filtre par dates ; la copie peut être partielle.",
    }.get(code, f"imapsync a signalé une erreur (code {code}). Consulte le journal ; la copie peut être partielle.")
