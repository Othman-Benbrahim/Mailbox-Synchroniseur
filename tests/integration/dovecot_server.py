"""Isolated Dovecot 2.3 fixture. Never starts or reconfigures a system service."""
import grp
import imaplib
import os
from pathlib import Path
import pwd
import signal
import socket
import ssl
import subprocess
import time

PASSWORD = "mailbox-test-password"


class DovecotServer:
    security = "SSL"

    def __init__(self, executable, directory, cert, key, limit="64K"):
        self.executable = str(executable)
        self.directory = Path(directory)
        self.directory.mkdir()
        self.cert = Path(cert)
        self.key = Path(key)
        self.limit = limit
        self.process = None
        self.log = self.directory / "server.log"
        self.config = self.directory / "dovecot.conf"
        self.password_file = self.directory / "users"
        self.password_file.write_text(f"test:{{PLAIN}}{PASSWORD}\n", encoding="utf-8")
        self.password_file.chmod(0o600)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]

    def write_config(self):
        user = pwd.getpwuid(os.getuid()).pw_name
        group = grp.getgrgid(os.getgid()).gr_name
        self.config.write_text(f"""
protocols = imap
listen = 127.0.0.1
base_dir = {self.directory}/run
state_dir = {self.directory}/state
default_internal_user = {user}
default_login_user = {user}
default_internal_group = {group}
first_valid_uid = {os.getuid()}
first_valid_gid = {os.getgid()}
log_path = {self.log}
ssl = required
ssl_cert = <{self.cert}
ssl_key = <{self.key}
auth_mechanisms = plain login
mail_home = {self.directory}/home
mail_location = maildir:{self.directory}/mail
mailbox_list_index = yes
mail_plugins = quota imap_quota
passdb {{
 driver = passwd-file
 args = {self.password_file}
}}
userdb {{
 driver = static
 args = uid={os.getuid()} gid={os.getgid()} home={self.directory}/home
}}
plugin {{
 quota = count:User quota
 quota_rule = *:storage={self.limit}
 quota_grace = 0
}}
service anvil {{
 chroot =
}}
service imap-login {{
 chroot =
 inet_listener imap {{
  port = 0
 }}
 inet_listener imaps {{
  port = {self.port}
  ssl = yes
 }}
}}
service auth-worker {{
 user = {user}
}}
""", encoding="utf-8")
        self.config.chmod(0o600)

    def connect(self):
        client = imaplib.IMAP4_SSL("localhost", self.port, timeout=3,
                                  ssl_context=ssl.create_default_context(cafile=str(self.cert)))
        try:
            client.login("test", PASSWORD)
        except Exception:
            client.shutdown()
            raise
        return client

    def start(self):
        self.write_config()
        with self.log.open("a") as output:
            self.process = subprocess.Popen([self.executable, "-F", "-c", str(self.config)],
                                            stdout=output, stderr=subprocess.STDOUT,
                                            start_new_session=True)
        deadline = time.monotonic() + 15
        try:
            while self.process.poll() is None:
                try:
                    client = self.connect()
                    client.logout()
                    return
                except (OSError, imaplib.IMAP4.error):
                    if time.monotonic() >= deadline:
                        break
                    time.sleep(0.1)
            raise RuntimeError("Dovecot did not start:\n" + self.log.read_text(errors="replace"))
        except Exception:
            self.stop()
            raise

    def stop(self):
        process, self.process = self.process, None
        if process is None:
            return
        # Only this fixture's process group: the system daemon is never touched.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)

    def increase_quota(self):
        self.stop()
        self.limit = "1M"
        self.start()
