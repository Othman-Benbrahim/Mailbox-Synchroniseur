import base64
import json
from pathlib import Path
import sys
import pytest
from mailbox_sync.engine import command, Redactor
from mailbox_sync.models import Account, Mode, Plan, validate_passwords
from mailbox_sync.profiles import load_profile, save_profile


def plan():
    return Plan(Account("source.example", "user & $(whoami)"),
                Account("destination.example", "other"), sys.executable)


@pytest.mark.parametrize("mode", list(Mode))
def test_no_destructive_operations_or_password_arguments(mode):
    program, args = command(plan(), mode)
    assert Path(program).is_file()
    assert "user & $(whoami)" in args
    assert not any(a.startswith(("--delete", "--expunge", "--password", "--showpassword")) for a in args)
    assert {"--noexpunge1", "--noexpunge2", "--nolog", "--noreleasecheck"} <= set(args)
    assert ("--dry" in args) == (mode == Mode.PREVIEW)
    assert ("--justlogin" in args) == (mode == Mode.LOGIN)
    assert args[args.index("--regexflag") + 1] == r"s/\\Deleted//g"


@pytest.mark.parametrize("security", ["SSL", "STARTTLS"])
def test_both_connections_force_tls_and_verify_identity(security):
    p = Plan(Account("source.example", "one", 993, security),
             Account("destination.example", "two", 993, security), sys.executable)
    _, args = command(p, Mode.COPY)
    for index, host in ((1, "source.example"), (2, "destination.example")):
        assert f"--{'ssl' if security == 'SSL' else 'tls'}{index}" in args
        ssl_opts = [args[i+1] for i, arg in enumerate(args) if arg == f"--sslargs{index}"]
        assert "SSL_verify_mode=1" in ssl_opts
        assert "SSL_verifycn_scheme=imap" in ssl_opts
        assert f"SSL_verifycn_name={host}" in ssl_opts


@pytest.mark.parametrize("host", ["", "https://imap.example", "x/y", "a b", "-host", "host\nfoo"])
def test_invalid_hosts_rejected(host):
    with pytest.raises(ValueError):
        Account(host, "user").validate()


@pytest.mark.parametrize("port", [0, 65536, "993", True])
def test_invalid_ports_rejected(port):
    with pytest.raises(ValueError):
        Account("source.example", "user", port).validate()


def test_same_account_rejected():
    with pytest.raises(ValueError):
        Plan(Account("Source.Example.", "user"), Account("source.example", "user"), sys.executable).validate()


@pytest.mark.parametrize("passwords", [("", "x"), ("x\ny", "x"), ("x\0", "y"), ("x",)])
def test_bad_passwords_rejected(passwords):
    with pytest.raises(ValueError):
        validate_passwords(passwords)


def test_profile_roundtrip_and_no_secret_fields(tmp_path):
    path = tmp_path / "profile.json"
    save_profile(path, plan())
    assert load_profile(path) == plan()
    assert "password" not in path.read_text()
    assert not list(tmp_path.glob(".mailbox-*"))
    data = json.loads(path.read_text())
    data["source"]["password"] = "should-never-be-loaded"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_profile(path)


@pytest.mark.parametrize("content", ['[]', '{"version": 2}', '{"version": 1, "source": null}', 'broken'])
def test_corrupt_profile(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content)
    with pytest.raises(ValueError):
        load_profile(path)


def test_redactor():
    secret = "sëcret &/"
    r = Redactor((secret,))
    assert secret not in r.clean(f"pwd={secret}")
    assert base64.b64encode(secret.encode()).decode() not in r.clean(base64.b64encode(secret.encode()).decode())
    assert r.clean("\x1b[31mOK\x1b[0m") == "OK"


def test_option_like_user_is_rejected():
    with pytest.raises(ValueError):
        Account("source.example", "--delete1").validate()
