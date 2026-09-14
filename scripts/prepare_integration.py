"""Fetch test-only dependencies from official sources, verifying exact bytes."""
import argparse
import hashlib
from pathlib import Path
import urllib.request

ASSETS = {
    "imapsync": (
        "https://raw.githubusercontent.com/imapsync/imapsync/93654c6025ff7814f983ab74dd300f9bed9282d9/imapsync",
        "89faed96f7c389723ddd7e78a00421b90d5b85bf79407fcf1b11209f3d4d7416",
    ),
    "greenmail-2.1.3.jar": (
        "https://repo.maven.apache.org/maven2/com/icegreen/greenmail-standalone/2.1.3/greenmail-standalone-2.1.3.jar",
        "9457fdaf45ded6c87bf84a321a5ced4b4b5e72b1d03686b778df381378afc4c8",
    ),
}


def prepare(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name, (url, digest) in ASSETS.items():
        target = folder / name
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != digest:
                raise RuntimeError(f"Checksum mismatch: {name}")
            target.write_bytes(data)
        if name == "imapsync":
            target.chmod(0o755)
        print(target.resolve())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".test-tools"))
    prepare(parser.parse_args().output)
