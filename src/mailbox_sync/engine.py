"""Pure command construction. No arbitrary command-line options are accepted."""
from pathlib import Path
import base64
import re
from urllib.parse import quote
from .models import Mode, Plan


def command(plan: Plan, mode: Mode) -> tuple[str, list[str]]:
    plan.validate()
    mode = Mode(mode)
    engine = Path(plan.engine).expanduser().resolve()
    if not engine.is_file():
        raise ValueError("Exécutable imapsync introuvable. Sélectionne son fichier.")
    args = ["--noreleasecheck", "--nolog", "--noexpunge1", "--noexpunge2",
            "--noresyncflags", "--regexflag", r"s/\\Deleted//g"]
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
    }.get(code, f"imapsync a signalé une erreur (code {code}). Consulte le journal ; la copie peut être partielle.")
