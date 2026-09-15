"""Runs the actual Perl engine over TLS to independent GreenMail servers."""
from dataclasses import replace
from email.message import EmailMessage
from email.policy import SMTP
import hashlib
import imaplib
import os
import re
import subprocess
import pytest
from mailbox_sync.engine import command
from mailbox_sync.folders import imap_utf7
from mailbox_sync.models import Account, Filters, FolderMapping, Mode, Plan
from mailbox_sync.report import MigrationReport
from mailbox_sync.runner import Runner

pytestmark = pytest.mark.integration
PASSWORD = "mailbox-test-password"
DATE = '"14-Sep-2020 13:20:00 +0000"'


def plan(pair, **options):
    source, destination, engine = pair
    return Plan(Account("localhost", "test", source.port, source.security),
                Account("localhost", "test", destination.port, destination.security), engine, **options)


def message(index, attachment=True):
    msg = EmailMessage(policy=SMTP)
    msg["From"] = "source@example.invalid"
    msg["To"] = "destination@example.invalid"
    msg["Subject"] = f"Message {index} — accents é et 日本語"
    msg["Message-ID"] = f"<fixture-{index}@example.invalid>"
    msg["Date"] = "Mon, 14 Sep 2020 13:20:00 +0000"
    msg.set_content("Texte UTF-8 : café, été, 日本語.\n")
    if attachment:
        msg.add_attachment(bytes(range(256)) * 64, maintype="application", subtype="octet-stream", filename="données.bin")
    return msg.as_bytes()


def quoted(folder):
    return '"' + imap_utf7(folder).replace('\\', '\\\\').replace('"', '\\"') + '"'


def seed(server, folder="INBOX", count=3, offset=0, dates=None, attachment=True):
    client = server.connect()
    try:
        if folder != "INBOX":
            assert client.create(quoted(folder))[0] == "OK"
        for index in range(count):
            flags = ("(\\Seen \\Flagged)", "(\\Answered)", "(\\Deleted)")[index % 3]
            date = DATE if dates is None else dates[index]
            assert client.append(quoted(folder), flags, date, message(index + offset, attachment))[0] == "OK"
    finally:
        client.logout()


def snapshot(server, folder="INBOX"):
    client = server.connect()
    try:
        if client.select(quoted(folder), readonly=True)[0] != "OK":
            return []
        status, data = client.search(None, "ALL")
        assert status == "OK"
        result = []
        for uid in data[0].split():
            status, fetched = client.fetch(uid, "(BODY.PEEK[] FLAGS INTERNALDATE)")
            assert status == "OK"
            literal = next(item for item in fetched if isinstance(item, tuple))
            metadata = b" ".join(item[0] if isinstance(item, tuple) else item for item in fetched)
            flags = set(imaplib.ParseFlags(metadata)) - {b"\\Recent"}
            date = re.search(rb'INTERNALDATE "([^"]+)"', metadata)[1]
            result.append((hashlib.sha256(literal[1]).hexdigest(), flags, date))
        return result
    finally:
        client.logout()


def run_sync(p, mode=Mode.COPY, password1=PASSWORD, password2=PASSWORD, environment=None, cwd=None):
    executable, arguments = command(p, mode)
    env = dict(os.environ, IMAPSYNC_PASSWORD1=password1, IMAPSYNC_PASSWORD2=password2)
    if environment:
        env.update(environment)
    result = subprocess.run([executable, *arguments], env=env, cwd=cwd, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=45)
    report = MigrationReport(mode=mode, exit_code=result.returncode, size_filter=(
        p.filters.max_size is not None or p.filters.min_size is not None))
    for line in result.stdout.splitlines():
        report.feed(line)
    return result, report


def test_copy_integrity_flags_dates_no_deletion_and_no_duplicates(pair, tmp_path):
    source, destination, _ = pair
    seed(source)
    seed(destination, count=1, offset=100)
    before_source, before_dest = snapshot(source), snapshot(destination)
    preview, _ = run_sync(plan(pair), Mode.PREVIEW, cwd=tmp_path)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert snapshot(source) == before_source
    assert snapshot(destination) == before_dest
    copied, report = run_sync(plan(pair), cwd=tmp_path)
    assert copied.returncode == 0, copied.stdout + copied.stderr
    assert snapshot(source) == before_source
    expected = before_dest + [(digest, flags - {b"\\Deleted"}, date) for digest, flags, date in before_source]
    assert snapshot(destination) == expected
    assert report.transferred == 3
    assert report.destination_confirmed
    repeated, report = run_sync(plan(pair), cwd=tmp_path)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert report.transferred == 0
    assert snapshot(destination) == expected


def test_unicode_nested_selection_and_mapping(pair, tmp_path):
    source, destination, _ = pair
    seed(source, count=1)
    seed(source, "Archives/Été & 日本語", count=2, offset=20)
    p = plan(pair, folders=(FolderMapping("Archives/Été & 日本語", "Copie/Été & 日本語"),))
    before = snapshot(source, "Archives/Été & 日本語")
    copied, report = run_sync(p, cwd=tmp_path)
    assert copied.returncode == 0, copied.stdout + copied.stderr
    assert snapshot(destination) == []
    assert snapshot(destination, "Copie/Été & 日本語") == before
    assert snapshot(source, "Archives/Été & 日本語") == before
    assert report.transferred == 2


@pytest.mark.parametrize("side", [1, 2])
def test_bad_password_refused(pair, tmp_path, side):
    result, _ = run_sync(plan(pair), Mode.LOGIN, cwd=tmp_path, **{f"password{side}": "wrong"})
    assert result.returncode in (16, 161, 162), result.stdout + result.stderr
    assert snapshot(pair[1]) == []


@pytest.mark.parametrize("failure", ["certificate", "hostname"])
@pytest.mark.parametrize("security", ["SSL", "STARTTLS"])
def test_tls_refusals(request, tmp_path, failure, security):
    pair = request.getfixturevalue("pair" if security == "SSL" else "starttls_pair")
    p = plan(pair)
    options = {}
    if security == "STARTTLS":
        p = replace(p, source=replace(p.source, port=pair[0].tls_port, security=security))
    if failure == "certificate":
        options["environment"] = {"SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt"}
    else:
        p = replace(p, source=replace(p.source, host="127.0.0.1"))
    result, report = run_sync(p, Mode.LOGIN, cwd=tmp_path, **options)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not report.destination_confirmed
    assert snapshot(pair[1]) == []


def test_starttls_copy(starttls_pair, tmp_path):
    pair = starttls_pair
    p = plan(pair)
    p = replace(p, source=replace(p.source, port=pair[0].tls_port, security="STARTTLS"),
                destination=replace(p.destination, port=pair[1].tls_port, security="STARTTLS"))
    seed(pair[0], count=1)
    result, report = run_sync(p, cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert report.transferred == 1
    assert snapshot(pair[1]) == snapshot(pair[0])


def test_server_announces_full_quota(pair, app, until):
    seed(pair[0], count=1)
    seed(pair[1], count=1, offset=100)
    before = snapshot(pair[1])
    client = pair[1].connect()
    try:
        assert client.setquota('INBOX', '(STORAGE 1)')[0] == "OK"
    finally:
        client.logout()
    # GreenMail reports usage, but does not enforce APPEND refusal. Verify the
    # real engine reports this quota failure even if some messages were accepted.
    runner = Runner()
    results = []
    runner.done.connect(lambda ok, text: results.append((ok, text)))
    runner.start(plan(pair), Mode.COPY, (PASSWORD, PASSWORD))
    try:
        until(lambda: bool(results), seconds=45)
        assert not results[0][0], results
        assert runner.report.errors > 0
        assert not runner.report.destination_confirmed
        assert snapshot(pair[1])[:len(before)] == before
    finally:
        if runner.active:
            runner.stop()
            until(lambda: not runner.active, seconds=5)


def test_real_qprocess_runner(pair, app, until):
    seed(pair[0], count=1)
    runner = Runner()
    results = []
    runner.done.connect(lambda ok, text: results.append((ok, text)))
    runner.start(plan(pair), Mode.COPY, (PASSWORD, PASSWORD))
    try:
        until(lambda: bool(results), seconds=45)
        assert results[0][0], results
        assert runner.report.transferred == 1
        assert runner.report.destination_confirmed
        assert snapshot(pair[1]) == snapshot(pair[0])
    finally:
        if runner.active:
            runner.stop()
            until(lambda: not runner.active, seconds=5)


def test_resume_after_real_network_interruption(pair, app, until, tmp_path, monkeypatch):
    from PySide6.QtCore import QTimer
    from relay import Relay
    seed(pair[0], count=6)
    before = snapshot(pair[0])
    relay = Relay(pair[0].port)
    p = plan(pair)
    routed = replace(p, source=replace(p.source, port=relay.port))
    real_command = command
    def slow_command(plan, mode):
        executable, args = real_command(plan, mode)
        return executable, args + ["--maxmessagespersecond", "1"]
    monkeypatch.setattr("mailbox_sync.runner.command", slow_command)
    runner = Runner()
    results, interrupted = [], []
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(runner.stop)
    def on_line(line):
        if " copied to " in line and not interrupted:
            interrupted.append(True)
            relay.cut()
            # The actual TCP stream is gone. Bound the engine's retry interval.
            timer.start(500)
    runner.line.connect(on_line)
    runner.done.connect(lambda ok, text: results.append((ok, text)))
    runner.start(routed, Mode.COPY, (PASSWORD, PASSWORD))
    try:
        until(lambda: bool(results), seconds=30)
        assert interrupted, "No transferred message observed before interruption"
        partial = snapshot(pair[1])
        assert 0 < len(partial) < len(before)
        assert not runner.report.destination_confirmed
        assert snapshot(pair[0]) == before
    finally:
        timer.stop()
        relay.cut()
        if runner.active:
            runner.stop()
            until(lambda: not runner.active, seconds=5)
    preview, _ = run_sync(p, Mode.PREVIEW, cwd=tmp_path)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    resumed, report = run_sync(p, cwd=tmp_path)
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert report.destination_confirmed
    assert report.transferred == len(before) - len(partial)
    expected = [(digest, flags - {b"\\Deleted"}, date) for digest, flags, date in before]
    assert snapshot(pair[1]) == expected
    assert snapshot(pair[0]) == before


def test_starttls_unavailable_never_falls_back_to_cleartext(pair, tmp_path):
    p = plan(pair)
    p = replace(p, source=replace(p.source, port=pair[0].tls_port, security="STARTTLS"))
    result, _ = run_sync(p, Mode.LOGIN, cwd=tmp_path)
    assert result.returncode == 12, result.stdout + result.stderr
    assert "Can not go to tls encryption on host1" in result.stdout
    assert snapshot(pair[1]) == []


def test_dovecot_strict_quota_refuses_append_and_resumes(quota_pair, app, until, tmp_path):
    source, destination, _ = quota_pair
    seed(source, count=1)
    seed(destination, count=2, offset=100)
    before_source, before_destination = snapshot(source), snapshot(destination)
    p = plan(quota_pair)

    preview, _ = run_sync(p, Mode.PREVIEW, cwd=tmp_path)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert snapshot(source) == before_source
    assert snapshot(destination) == before_destination

    # Actual server rejection, not a mocked APPEND or an announced quota alone.
    client = destination.connect()
    try:
        status, response = client.append("INBOX", "(\\Seen)", DATE, message(999))
        assert status == "NO", response
        assert b"OVERQUOTA" in b" ".join(response).upper(), response
    finally:
        client.logout()
    assert snapshot(destination) == before_destination

    runner = Runner()
    results, lines = [], []
    runner.done.connect(lambda ok, text: results.append((ok, text)))
    runner.line.connect(lines.append)
    runner.start(p, Mode.COPY, (PASSWORD, PASSWORD))
    try:
        until(lambda: bool(results), seconds=45)
        assert not results[0][0], results
        assert any("OVERQUOTA" in line.upper() for line in lines), "\n".join(lines)
        assert runner.report.errors is not None and runner.report.errors > 0
        assert runner.report.transferred == 0
        assert not runner.report.destination_confirmed
        assert snapshot(source) == before_source
        assert snapshot(destination) == before_destination
    finally:
        if runner.active:
            runner.stop()
            until(lambda: not runner.active, seconds=5)

    # Restart the same destination with more space, retaining its Maildir.
    destination.increase_quota()
    assert snapshot(destination) == before_destination
    preview, _ = run_sync(p, Mode.PREVIEW, cwd=tmp_path)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert snapshot(destination) == before_destination
    copied, report = run_sync(p, cwd=tmp_path)
    assert copied.returncode == 0, copied.stdout + copied.stderr
    assert report.transferred == 1 and report.destination_confirmed
    expected = before_destination + before_source
    assert snapshot(destination) == expected
    assert snapshot(source) == before_source
    repeated, report = run_sync(p, cwd=tmp_path)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert report.transferred == 0 and report.destination_confirmed
    assert snapshot(destination) == expected


def sizes(server, folder="INBOX"):
    """RFC822.SIZE of every message, as the engine reads it for its statistics."""
    client = server.connect()
    try:
        assert client.select(quoted(folder), readonly=True)[0] == "OK"
        status, data = client.search(None, "ALL")
        assert status == "OK"
        result = []
        for uid in data[0].split():
            status, fetched = client.fetch(uid, "(RFC822.SIZE)")
            assert status == "OK"
            result.append(int(re.search(rb"RFC822\.SIZE (\d+)", fetched[0])[1]))
        return result
    finally:
        client.logout()


def filtered_plan(request, kind, **options):
    """Both server families: GreenMail in TLS direct, pymap in STARTTLS."""
    pair = request.getfixturevalue("pair" if kind == "SSL" else "starttls_pair")
    p = plan(pair, **options)
    if kind == "STARTTLS":
        p = replace(p, source=replace(p.source, port=pair[0].tls_port, security="STARTTLS"),
                    destination=replace(p.destination, port=pair[1].tls_port, security="STARTTLS"))
    return pair, p


@pytest.mark.parametrize("kind", ["SSL", "STARTTLS"])
def test_date_filter_selects_by_internal_date_and_estimates_volume(request, tmp_path, kind):
    pair, unfiltered = filtered_plan(request, kind)
    source, destination, _ = pair
    seed(source, count=3, dates=['"01-Jun-2019 10:00:00 +0000"', '"01-Jun-2020 10:00:00 +0000"',
                                 '"01-Jun-2021 10:00:00 +0000"'])
    before_source = snapshot(source)
    p = replace(unfiltered, filters=Filters(since="2020-01-01", until="2020-12-31"))
    preview, report = run_sync(p, Mode.PREVIEW, cwd=tmp_path)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert snapshot(destination) == [] and snapshot(source) == before_source
    assert report.plannable == 1, preview.stdout
    # The estimate is built from the sizes the server announces (RFC822.SIZE).
    assert report.source_bytes == sizes(source)[1], preview.stdout
    assert report.estimated_bytes == sizes(source)[1], preview.stdout
    copied, report = run_sync(p, cwd=tmp_path)
    assert copied.returncode == 0, copied.stdout + copied.stderr
    assert report.transferred == 1 and report.destination_confirmed
    # Transferred bytes are the real message bytes. GreenMail announces RFC822.SIZE
    # without headers, so its estimate undershoots; pymap and Dovecot announce
    # exact sizes and the two figures coincide there.
    assert report.transferred_bytes == len(message(1)), copied.stdout
    if kind == "STARTTLS":
        assert report.transferred_bytes == sizes(source)[1], copied.stdout
    digest, flags, date = before_source[1]
    assert snapshot(destination) == [(digest, flags - {b"\\Deleted"}, date)]
    assert snapshot(source) == before_source
    repeated, report = run_sync(p, cwd=tmp_path)
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert report.transferred == 0 and report.destination_confirmed
    # Widening the window copies the rest without recopying the 2020 message.
    widened, report = run_sync(replace(unfiltered, filters=Filters(since="2019-01-01")), cwd=tmp_path)
    assert widened.returncode == 0, widened.stdout + widened.stderr
    assert report.transferred == 2 and report.destination_confirmed
    assert sorted(snapshot(destination)) == sorted(
        (digest, flags - {b"\\Deleted"}, date) for digest, flags, date in before_source)


@pytest.mark.parametrize("kind", ["SSL", "STARTTLS"])
def test_size_filter_skips_large_messages_and_accounts_for_them(request, tmp_path, kind):
    pair, unfiltered = filtered_plan(request, kind)
    source, destination, _ = pair
    seed(source, count=1)                                # attachment: well above 4 KiB
    seed(source, count=1, offset=10, attachment=False)   # text only: below 4 KiB
    before_source = snapshot(source)
    small, large = sizes(source)[1], sizes(source)[0]
    assert small < 4096 < large
    p = replace(unfiltered, filters=Filters(max_size=4096))
    preview, report = run_sync(p, Mode.PREVIEW, cwd=tmp_path)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert snapshot(destination) == []
    # Simulation does not fetch messages, so it cannot apply the size filter:
    # the estimate is an upper bound and the report says so.
    assert report.plannable == 2 and report.estimated_bytes == small + large, preview.stdout
    assert "avant filtre de taille" in report.text()
    copied, report = run_sync(p, cwd=tmp_path)
    assert copied.returncode == 0, copied.stdout + copied.stderr
    assert report.transferred == 1 and report.skipped == 1, copied.stdout
    assert report.size_filtered == 1 and report.missing == 1, copied.stdout
    assert report.unexplained_missing == 0 and report.destination_confirmed
    # Skipped bytes come from the announced size the filter was applied to;
    # transferred bytes are the real bytes of the small message (see date test).
    assert report.skipped_bytes == large, copied.stdout
    assert report.transferred_bytes == len(message(10, attachment=False)), copied.stdout
    if kind == "STARTTLS":
        assert report.transferred_bytes == small, copied.stdout
    digest, flags, date = before_source[1]
    assert snapshot(destination) == [(digest, flags - {b"\\Deleted"}, date)]
    assert snapshot(source) == before_source
    # Without the filter, the large message is copied and nothing is recopied.
    resumed, report = run_sync(unfiltered, cwd=tmp_path)
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert report.transferred == 1 and report.size_filtered == 0 and report.destination_confirmed
    assert sorted(snapshot(destination)) == sorted(
        (digest, flags - {b"\\Deleted"}, date) for digest, flags, date in before_source)


@pytest.mark.parametrize("kind", ["SSL", "STARTTLS"])
def test_discovery_lists_folders_over_verified_tls_and_proposal_drives_a_real_copy(request, tmp_path, kind):
    from mailbox_sync.discovery import DiscoveryError, list_folders
    from mailbox_sync.mapping import propose
    pair, unfiltered = filtered_plan(request, kind)
    source, destination, _ = pair
    seed(source, count=1)
    seed(source, "Envoyés", count=2, offset=20)
    seed(source, "Archives/Été", count=1, offset=40)
    seed(destination, "Sent Items", count=1, offset=100)
    before_sent_items = snapshot(destination, "Sent Items")

    # Read-only discovery with the same TLS requirements as the engine.
    listed_source = list_folders(unfiltered.source, PASSWORD)
    listed_destination = list_folders(unfiltered.destination, PASSWORD)
    assert {"INBOX", "Envoyés", "Archives/Été"} <= {f.name for f in listed_source}
    assert {"INBOX", "Sent Items"} <= {f.name for f in listed_destination}
    assert all(f.raw == imap_utf7(f.name) for f in listed_source)
    with pytest.raises(DiscoveryError):
        list_folders(unfiltered.source, "wrong")
    with pytest.raises(DiscoveryError):   # certificate is for "localhost", not for the IP
        list_folders(replace(unfiltered.source, host="127.0.0.1"), PASSWORD)
    assert snapshot(destination, "Sent Items") == before_sent_items   # nothing written by discovery

    proposals = propose(listed_source, listed_destination)
    mappings = {p.source: p.mapping for p in proposals if p.mapping is not None}
    assert mappings["INBOX"] == FolderMapping("INBOX", "")
    assert mappings["Envoyés"] == FolderMapping("Envoyés", "Sent Items")
    assert mappings["Archives/Été"] == FolderMapping("Archives/Été", "")
    selected = tuple(p.mapping for p in proposals if p.mapping is not None)
    p = replace(unfiltered, folders=selected)
    preview, _ = run_sync(p, Mode.PREVIEW, cwd=tmp_path)
    assert preview.returncode == 0, preview.stdout + preview.stderr
    copied, report = run_sync(p, cwd=tmp_path)
    assert copied.returncode == 0, copied.stdout + copied.stderr
    assert report.transferred == 4 and report.destination_confirmed
    expected_sent = before_sent_items + [(d, f - {b"\\Deleted"}, t) for d, f, t in snapshot(source, "Envoyés")]
    assert snapshot(destination, "Sent Items") == expected_sent
    assert snapshot(destination, "Archives/Été") == snapshot(source, "Archives/Été")
    assert snapshot(destination) == snapshot(source)
    assert snapshot(destination, "Envoyés") == []


def test_history_of_a_real_run_carries_no_secret_and_matches_the_engine(pair, app, until, tmp_path, monkeypatch):
    """The history entry of an actual imapsync run reproduces its counters and
    contains neither the password nor the session log."""
    from mailbox_sync import history
    monkeypatch.setenv("MAILBOX_HISTORY_DIR", str(tmp_path / "historique"))
    directory = tmp_path / "historique"
    source, destination, _ = pair
    seed(source, count=2)
    p = plan(pair, folders=(FolderMapping("INBOX", ""),))
    runner = Runner()
    results = []
    runner.done.connect(lambda ok, text: results.append((ok, text)))
    started = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    runner.start(p, Mode.COPY, (PASSWORD, PASSWORD))
    try:
        until(lambda: bool(results), seconds=45)
        assert results[0][0], results
    finally:
        if runner.active:
            runner.stop()
            until(lambda: not runner.active, seconds=5)
    path = history.save(history.build(p, runner.report, *results[0], started), directory)
    text = path.read_text(encoding="utf-8")
    assert PASSWORD not in text and "IMAPSYNC_PASSWORD" not in text
    entry = history.load(directory)[0]
    assert entry.counters["transferred"] == runner.report.transferred == 2
    assert entry.counters["transferred_bytes"] == runner.report.transferred_bytes
    assert entry.counters["destination_confirmed"] is True
    assert entry.folders == [{"source": "INBOX", "destination": ""}]
    report = history.report_text(entry)
    assert PASSWORD not in report and "Copiés              : 2" in report
    assert snapshot(destination) == snapshot(source)
