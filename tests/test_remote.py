#!/usr/bin/env python
# vim: set et ts=8 sts=4 sw=4 ai

import os
import pytest
from base64 import b64encode


@pytest.fixture
def create_app_with_git(create_app):
    create_app.config["GIT_WEB_SERVER"] = True
    yield create_app
    create_app.config["GIT_WEB_SERVER"] = False


@pytest.fixture
def test_client_with_git(create_app_with_git):
    client = create_app_with_git.test_client()
    return client


def test_git_info_refs_404(create_app, test_client):
    rv = test_client.get(
        "/.git/info/refs?service=git-upload-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 404

    rv = test_client.get(
        "/.git/info/refs?service=git-receive-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 404

    rv = test_client.post("/.git/git-upload-pack")
    assert rv.status_code == 404

    rv = test_client.post("/.git/git-receive-pack")
    assert rv.status_code == 404


def test_git_info_refs(create_app_with_git, test_client_with_git):
    create_app_with_git.config["READ_ACCESS"] = "ANONYMOUS"
    create_app_with_git.config["WRITE_ACCESS"] = "ANONYMOUS"
    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-upload-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 200
    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-receive-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 200

    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-random-service",
        follow_redirects=True,
    )
    assert rv.status_code == 400


def test_git_info_refs_permissions(create_app_with_git, test_client_with_git):
    create_app_with_git.config["READ_ACCESS"] = "ANONYMOUS"
    create_app_with_git.config["WRITE_ACCESS"] = "ANONYMOUS"
    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-upload-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 200
    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-receive-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 200
    create_app_with_git.config["WRITE_ACCESS"] = "ADMIN"

    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-upload-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 200
    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-receive-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 401

    create_app_with_git.config["READ_ACCESS"] = "ADMIN"

    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-upload-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 401
    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-receive-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 401


def test_git_pack(create_app_with_git, test_client_with_git):
    create_app_with_git.config["READ_ACCESS"] = "ANONYMOUS"
    create_app_with_git.config["WRITE_ACCESS"] = "ANONYMOUS"
    create_app_with_git.config["ATTACHMENT_ACCESS"] = "ANONYMOUS"
    rv = test_client_with_git.get(
        "/.git/info/refs?service=git-upload-pack",
        follow_redirects=True,
    )
    rv = test_client_with_git.post(
        "/.git/git-upload-pack",
    )
    # We expect 500 here, since we are not providing the correct data=b'00a8want ... multi_ack_detailed no-done side-band-64k thin-pack ofs-delta deepen-since deepen-not ...'
    assert rv.status_code == 500

    rv = test_client_with_git.post("/.git/git-receive-pack")
    assert rv.status_code == 500

    create_app_with_git.config["ATTACHMENT_ACCESS"] = "ADMIN"
    rv = test_client_with_git.post("/.git/git-upload-pack")
    assert rv.status_code == 500

    rv = test_client_with_git.post("/.git/git-receive-pack")
    assert rv.status_code == 401


def test_git_pack_auth(app_with_user):
    test_client = app_with_user.test_client()
    app_with_user.config["GIT_WEB_SERVER"] = True
    app_with_user.config["READ_ACCESS"] = "APPROVED"
    app_with_user.config["WRITE_ACCESS"] = "APPROVED"
    app_with_user.config["ATTACHMENT_ACCESS"] = "APPROVED"

    rv = test_client.get(
        "/.git/info/refs?service=git-upload-pack",
        follow_redirects=True,
    )
    assert rv.status_code == 401

    rv = test_client.get(
        "/.git/info/refs?service=git-upload-pack",
        follow_redirects=True,
        headers={
            "Authorization": "Basic {}".format(
                b64encode(b"test_user:test_password")
            )
        },
    )
    assert rv.status_code == 401

    credentials = b64encode(b"mail@example.org:password1234").decode('utf-8')

    rv = test_client.get(
        "/.git/info/refs?service=git-upload-pack",
        headers={"Authorization": f"Basic {credentials}"},
    )
    assert rv.status_code == 200

    app_with_user.config["GIT_WEB_SERVER"] = False
    app_with_user.config["READ_ACCESS"] = "ANONYMOUS"
    app_with_user.config["WRITE_ACCESS"] = "ANONYMOUS"
    app_with_user.config["ATTACHMENT_ACCESS"] = "ANONYMOUS"


def test_git_pack_auth_user(app_with_user):
    from otterwiki.auth import SimpleAuth, generate_password_hash, db
    from datetime import datetime

    app_with_user.config["GIT_WEB_SERVER"] = True
    # Lock down the wiki
    app_with_user.config["READ_ACCESS"] = "ADMIN"
    app_with_user.config["WRITE_ACCESS"] = "ADMIN"
    app_with_user.config["ATTACHMENT_ACCESS"] = "ADMIN"
    # create a user with permissions
    user = SimpleAuth.User(
        name="Configured User",  # pyright: ignore
        email="configured@user.org",  # pyright: ignore
        password_hash=generate_password_hash(
            "password1234", method="scrypt"
        ),  # pyright: ignore
        first_seen=datetime.now(),  # pyright: ignore
        last_seen=datetime.now(),  # pyright: ignore
        allow_read=True,  # pyright: ignore
        allow_write=True,  # pyright: ignore
        allow_upload=False,  # pyright: ignore
        is_approved=True,  # pyright: ignore
        is_admin=False,  # pyright: ignore
    )
    db.session.add(user)
    db.session.commit()

    test_client = app_with_user.test_client()
    admin_credentials = b64encode(b"mail@example.org:password1234").decode(
        'utf-8'
    )
    user_credentials = b64encode(b"configured@user.org:password1234").decode(
        'utf-8'
    )

    rv = test_client.get(
        "/.git/info/refs?service=git-upload-pack",
        headers={"Authorization": f"Basic {admin_credentials}"},
    )
    assert rv.status_code == 200
    rv = test_client.post(
        "/.git/git-receive-pack",
        headers={"Authorization": f"Basic {admin_credentials}"},
    )
    # 500 is in this test okay, since we are not sending the correct data
    assert rv.status_code == 500

    rv = test_client.get(
        "/.git/info/refs?service=git-upload-pack",
        headers={"Authorization": f"Basic {user_credentials}"},
    )
    # since our user has allow_read=True
    assert rv.status_code == 200

    rv = test_client.post(
        "/.git/git-receive-pack",
        headers={"Authorization": f"Basic {user_credentials}"},
    )
    # user has allow_upload == False
    assert rv.status_code == 403

    # update user
    user.allow_upload = True
    db.session.add(user)
    db.session.commit()

    rv = test_client.get(
        "/.git/info/refs?service=git-upload-pack",
        headers={"Authorization": f"Basic {user_credentials}"},
    )
    assert rv.status_code == 200

    app_with_user.config["GIT_WEB_SERVER"] = False
    app_with_user.config["READ_ACCESS"] = "ANONYMOUS"
    app_with_user.config["WRITE_ACCESS"] = "ANONYMOUS"
    app_with_user.config["ATTACHMENT_ACCESS"] = "ANONYMOUS"


def _config_writes(monkeypatch):
    """Record the `git config` writes GitHttpServer makes (reads have --get)."""
    import subprocess
    import otterwiki.remote

    writes = []
    real_run = subprocess.run

    def run(cmd, *args, **kwargs):
        if cmd[:2] == ["git", "config"] and "--get" not in cmd:
            writes.append(cmd)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(otterwiki.remote.subprocess, "run", run)
    return writes


def test_githttpserver_writes_config_only_when_needed(create_app, monkeypatch):
    import subprocess
    from otterwiki.remote import GitHttpServer

    path = create_app.config["REPOSITORY"]
    config_file = os.path.join(path, ".git", "config")
    subprocess.run(
        ["git", "config", "--file", config_file, "--unset", "receive.denyCurrentBranch"]
    )
    writes = _config_writes(monkeypatch)

    GitHttpServer(path=path)
    assert len(writes) == 1
    # every later construction (e.g. a tenant swap) only reads
    GitHttpServer(path=path)
    GitHttpServer(path=path)
    assert len(writes) == 1
    value = subprocess.run(
        ["git", "config", "--file", config_file, "receive.denyCurrentBranch"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert value == "updateInstead"


def test_githttpserver_lost_config_race_is_not_an_error(create_app, monkeypatch):
    """If another worker set the value while we held no lock, don't log."""
    import subprocess
    import otterwiki.remote
    from otterwiki.remote import GitHttpServer

    path = create_app.config["REPOSITORY"]
    config_file = os.path.join(path, ".git", "config")
    subprocess.run(
        ["git", "config", "--file", config_file, "--unset", "receive.denyCurrentBranch"]
    )
    real_run = subprocess.run

    def run(cmd, *args, **kwargs):
        if cmd[:2] == ["git", "config"] and "--get" not in cmd:
            # the other worker wins, then our write fails on config.lock
            real_run(cmd, *args, **kwargs)
            return subprocess.CompletedProcess(cmd, 255, b"", b"could not lock")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(otterwiki.remote.subprocess, "run", run)
    errors = []
    monkeypatch.setattr(otterwiki.remote.app.logger, "error", errors.append)
    GitHttpServer(path=path)
    assert errors == []
