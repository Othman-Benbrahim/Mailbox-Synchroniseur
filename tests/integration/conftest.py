"""Real, opt-in IMAP integration tests. No user accounts or external mail hosts."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import imaplib
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import time
import pytest

PASSWORD = "mailbox-test-password"
IMAPSYNC_SHA256 = "89faed96f7c389723ddd7e78a00421b90d5b85bf79407fcf1b11209f3d4d7416"
GREENMAIL_SHA256 = "9457fdaf45ded6c87bf84a321a5ced4b4b5e72b1d03686b778df381378afc4c8"


@pytest.fixture(scope="session")
def integration_tools(tmp_path_factory):
    if os.environ.get("MAILBOX_INTEGRATION") != "1":
        pytest.skip("Real IMAP tests disabled; see docs/INTEGRATION.md")
    engine = Path(os.environ["MAILBOX_IMAPSYNC"]).resolve()
    jar = Path(os.environ["MAILBOX_GREENMAIL_JAR"]).resolve()
    assert hashlib.sha256(engine.read_bytes()).hexdigest() == IMAPSYNC_SHA256
    assert hashlib.sha256(jar.read_bytes()).hexdigest() == GREENMAIL_SHA256
    for tool in ("java", "keytool", "perl"):
        assert shutil.which(tool), f"Missing test dependency: {tool}"
    assert subprocess.check_output([str(engine), "--version"], text=True, timeout=15).strip() == "2.314"
    folder = tmp_path_factory.mktemp("mailbox-tls")
    keystore, cert = folder / "server.p12", folder / "cert.pem"
    common = ["keytool", "-J-XX:ActiveProcessorCount=2", "-J-Xmx64m"]
    subprocess.run(common + ["-genkeypair", "-alias", "mailbox", "-keyalg", "RSA", "-keysize", "2048",
                   "-storetype", "PKCS12", "-keystore", str(keystore), "-storepass", PASSWORD,
                   "-keypass", PASSWORD, "-dname", "CN=localhost", "-ext", "SAN=dns:localhost",
                   "-validity", "2", "-noprompt"], check=True, capture_output=True, timeout=30)
    subprocess.run(common + ["-exportcert", "-alias", "mailbox", "-keystore", str(keystore),
                   "-storepass", PASSWORD, "-rfc", "-file", str(cert)], check=True, capture_output=True, timeout=30)
    return engine, jar, keystore, cert


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@dataclass
class Server:
    port: int
    tls_port: int
    cert: Path
    process: subprocess.Popen
    security: str = "SSL"

    def connect(self):
        context = ssl.create_default_context(cafile=str(self.cert))
        if self.security == "SSL":
            client = imaplib.IMAP4_SSL("localhost", self.port, timeout=5, ssl_context=context)
        else:
            client = imaplib.IMAP4("localhost", self.port, timeout=5)
            client.starttls(context)
        client.login("test", PASSWORD)
        return client


@contextmanager
def server(tools, directory):
    _, jar, keystore, cert = tools
    port, tls_port = free_port(), free_port()
    while tls_port == port:
        tls_port = free_port()
    command = ["java", "-XX:ActiveProcessorCount=2", "-Xms16m", "-Xmx64m", "-XX:+UseSerialGC",
               "-Xss256k", f"-Dgreenmail.imaps.port={port}", "-Dgreenmail.imaps.hostname=127.0.0.1",
               f"-Dgreenmail.imap.port={tls_port}", "-Dgreenmail.imap.hostname=127.0.0.1",
               f"-Dgreenmail.users=test:{PASSWORD}", f"-Dgreenmail.tls.keystore.file={keystore}",
               f"-Dgreenmail.tls.keystore.password={PASSWORD}", "-jar", str(jar)]
    log_path = directory / f"server-{port}.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        instance = Server(port, tls_port, cert, process)
        try:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise RuntimeError("GreenMail exited: " + log_path.read_text())
                try:
                    client = instance.connect()
                    client.logout()
                    break
                except (OSError, imaplib.IMAP4.error):
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.05)
            yield instance
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


@pytest.fixture
def pair(integration_tools, tmp_path, monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", str(integration_tools[3]))
    with server(integration_tools, tmp_path) as source, server(integration_tools, tmp_path) as destination:
        yield source, destination, str(integration_tools[0])


@contextmanager
def starttls_server(tools, directory, key):
    from importlib.metadata import version
    assert version("pymap") == "0.36.7"
    port = free_port()
    log_path = directory / f"pymap-{port}.log"
    command = [sys.executable, "-c", "from pymap.main import main; main()", "--host", "127.0.0.1", "--port", str(port),
               "--cert", str(tools[3]), "--key", str(key), "dict",
               "--demo-user", "test", "--demo-password", PASSWORD]
    with log_path.open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        instance = Server(port, port, tools[3], process, "STARTTLS")
        try:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise RuntimeError("pymap exited: " + log_path.read_text())
                try:
                    client = instance.connect()
                    client.logout()
                    break
                except (OSError, imaplib.IMAP4.error):
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.05)
            yield instance
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


@pytest.fixture
def starttls_pair(integration_tools, tmp_path, monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", str(integration_tools[3]))
    key = tmp_path / "test-key.pem"
    subprocess.run(["openssl", "pkcs12", "-in", str(integration_tools[2]), "-passin", f"pass:{PASSWORD}",
                    "-nocerts", "-nodes", "-out", str(key)], check=True, capture_output=True, timeout=15)
    key.chmod(0o600)
    with starttls_server(integration_tools, tmp_path, key) as source, starttls_server(integration_tools, tmp_path, key) as dest:
        yield source, dest, str(integration_tools[0])


@pytest.fixture
def dovecot_executable():
    executable = os.environ.get("MAILBOX_DOVECOT")
    if not executable:
        pytest.skip("Strict quota test requires MAILBOX_DOVECOT; see docs/INTEGRATION.md")
    assert sys.platform == "linux", "The strict quota fixture requires Linux"
    assert os.getuid() != 0, "Run the Dovecot fixture as an ordinary user, not root"
    version = subprocess.check_output([executable, "--version"], text=True, timeout=15).strip()
    assert version.split()[0] == "2.3.21", f"Unexpected Dovecot version: {version}"
    print("Strict quota server:", version)
    return executable


@pytest.fixture
def quota_pair(dovecot_executable, integration_tools, monkeypatch):
    import tempfile
    from dovecot_server import DovecotServer

    monkeypatch.setenv("SSL_CERT_FILE", str(integration_tools[3]))
    # Short path: Dovecot's internal Unix socket paths must stay below 108 bytes.
    with tempfile.TemporaryDirectory(prefix="mq-") as folder:
        root = Path(folder)
        key = root / "key.pem"
        subprocess.run(["openssl", "pkcs12", "-in", str(integration_tools[2]),
                        "-passin", f"pass:{PASSWORD}", "-nocerts", "-nodes", "-out", str(key)],
                       check=True, capture_output=True, timeout=15)
        key.chmod(0o600)
        source = DovecotServer(dovecot_executable, root / "source", integration_tools[3], key, "1M")
        destination = DovecotServer(dovecot_executable, root / "dest", integration_tools[3], key)
        try:
            source.start()
            destination.start()
            yield source, destination, str(integration_tools[0])
        finally:
            destination.stop()
            source.stop()
            for label, instance in (("source", source), ("destination", destination)):
                if instance.log.exists():
                    print(f"Dovecot {label} log:\n{instance.log.read_text(errors='replace')}")
