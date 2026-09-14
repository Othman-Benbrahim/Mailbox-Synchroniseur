"""A profile is an explicit allowlist; secrets never enter the serializer."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
from .models import Account, Plan


def save_profile(path: Path, plan: Plan):
    plan.validate()
    content = {"version": 1, "source": asdict(plan.source),
               "destination": asdict(plan.destination), "engine": plan.engine}
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
        if set(data) != {"version", "source", "destination", "engine"} or data["version"] != 1:
            raise ValueError("Format de profil non reconnu.")
        plan = Plan(Account(**data["source"]), Account(**data["destination"]), data["engine"])
        plan.validate()
        return plan
    except (TypeError, KeyError, AttributeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Profil invalide ou endommagé.") from exc
