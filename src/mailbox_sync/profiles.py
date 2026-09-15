"""Versioned, atomic, secret-free profile persistence (v1 and v2 remain readable)."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from .models import Account, Filters, FolderMapping, Plan


def save_profile(path: Path, plan: Plan):
    plan.validate()
    content = {"version": 3, "source": asdict(plan.source), "destination": asdict(plan.destination),
               "engine": plan.engine,
               "folders": None if plan.folders is None else [asdict(f) for f in plan.folders],
               "filters": asdict(plan.filters)}
    fd, temp = tempfile.mkstemp(prefix=".mailbox-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(content, out, indent=2, ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_profile(path: Path) -> Plan:
    if path.stat().st_size > 64 * 1024:
        raise ValueError("Profil trop volumineux.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        base = {"version", "source", "destination", "engine"}
        if type(data["version"]) is not int:
            raise ValueError("Version de profil invalide.")
        folders, filters = None, Filters()
        if data["version"] == 1 and set(data) == base:
            pass
        elif data["version"] in (2, 3) and set(data) == base | {"folders"} | ({"filters"} if data["version"] == 3 else set()):
            if data["folders"] is not None and not isinstance(data["folders"], list):
                raise ValueError("Liste de dossiers invalide.")
            folders = None if data["folders"] is None else tuple(FolderMapping(**item) for item in data["folders"])
            if data["version"] == 3:
                if not isinstance(data["filters"], dict):
                    raise ValueError("Filtres de profil invalides.")
                filters = Filters(**data["filters"])
        else:
            raise ValueError("Format de profil non reconnu.")
        plan = Plan(Account(**data["source"]), Account(**data["destination"]), data["engine"], folders, filters)
        plan.validate()
        return plan
    except (TypeError, KeyError, AttributeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Profil invalide ou endommagé.") from exc
