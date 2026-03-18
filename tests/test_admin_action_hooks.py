#!/usr/bin/env python

"""Tests for admin action hooks (permission_changed, user_flags_changed)."""

import sys

from otterwiki.plugins import hookimpl


def _get_plugin_manager():
    """Get the current plugin_manager, even after module reloads by other tests."""
    return sys.modules["otterwiki.plugins"].plugin_manager


class AdminHookRecorder:
    """Test plugin that records admin hook calls."""

    def __init__(self):
        self.calls = []

    @hookimpl
    def permission_changed(self, setting_name, old_value, new_value, author):
        self.calls.append(
            (
                "permission_changed",
                {
                    "setting_name": setting_name,
                    "old_value": old_value,
                    "new_value": new_value,
                    "author": author,
                },
            )
        )

    @hookimpl
    def user_flags_changed(self, user_email, changes, author):
        self.calls.append(
            (
                "user_flags_changed",
                {
                    "user_email": user_email,
                    "changes": changes,
                    "author": author,
                },
            )
        )


def make_recorder():
    recorder = AdminHookRecorder()
    _get_plugin_manager().register(recorder)
    return recorder


def _reset_access_settings(admin_client):
    """Reset access settings to app defaults to avoid leaking state between tests."""
    admin_client.post(
        "/-/admin/permissions_and_registration",
        data={
            "READ_access": "ANONYMOUS",
            "WRITE_access": "ANONYMOUS",
            "ATTACHMENT_access": "ANONYMOUS",
        },
        follow_redirects=True,
    )


def test_permission_changed_hook_fires(app_with_user, admin_client):
    """POST changing READ_ACCESS fires permission_changed hook."""
    recorder = make_recorder()
    try:
        rv = admin_client.post(
            "/-/admin/permissions_and_registration",
            data={
                "READ_access": "APPROVED",
                "WRITE_access": "REGISTERED",
                "ATTACHMENT_access": "REGISTERED",
            },
            follow_redirects=True,
        )
        assert rv.status_code == 200
        perm_calls = [
            c for c in recorder.calls if c[0] == "permission_changed"
        ]
        setting_names = [c[1]["setting_name"] for c in perm_calls]
        assert "READ_ACCESS" in setting_names
        read_call = next(
            c[1] for c in perm_calls if c[1]["setting_name"] == "READ_ACCESS"
        )
        assert read_call["new_value"] == "APPROVED"
        assert read_call["author"] is not None
    finally:
        _get_plugin_manager().unregister(recorder)
        _reset_access_settings(admin_client)


def test_permission_changed_hook_not_fired_when_unchanged(
    app_with_user, admin_client
):
    """POST with same values does not fire permission_changed hook."""
    # First, set values to known state
    admin_client.post(
        "/-/admin/permissions_and_registration",
        data={
            "READ_access": "ANONYMOUS",
            "WRITE_access": "REGISTERED",
            "ATTACHMENT_access": "REGISTERED",
        },
        follow_redirects=True,
    )
    recorder = make_recorder()
    try:
        # POST same values again
        rv = admin_client.post(
            "/-/admin/permissions_and_registration",
            data={
                "READ_access": "ANONYMOUS",
                "WRITE_access": "REGISTERED",
                "ATTACHMENT_access": "REGISTERED",
            },
            follow_redirects=True,
        )
        assert rv.status_code == 200
        assert len(recorder.calls) == 0
    finally:
        _get_plugin_manager().unregister(recorder)
        _reset_access_settings(admin_client)


def test_permission_changed_multiple_settings(app_with_user, admin_client):
    """Changing all three access settings fires 3 hook calls."""
    # Set known state first
    admin_client.post(
        "/-/admin/permissions_and_registration",
        data={
            "READ_access": "ANONYMOUS",
            "WRITE_access": "ANONYMOUS",
            "ATTACHMENT_access": "ANONYMOUS",
        },
        follow_redirects=True,
    )
    recorder = make_recorder()
    try:
        rv = admin_client.post(
            "/-/admin/permissions_and_registration",
            data={
                "READ_access": "APPROVED",
                "WRITE_access": "REGISTERED",
                "ATTACHMENT_access": "APPROVED",
            },
            follow_redirects=True,
        )
        assert rv.status_code == 200
        perm_calls = [
            c for c in recorder.calls if c[0] == "permission_changed"
        ]
        assert len(perm_calls) == 3
        setting_names = {c[1]["setting_name"] for c in perm_calls}
        assert setting_names == {
            "READ_ACCESS",
            "WRITE_ACCESS",
            "ATTACHMENT_ACCESS",
        }
    finally:
        _get_plugin_manager().unregister(recorder)
        _reset_access_settings(admin_client)


def test_user_flags_changed_hook_fires_from_user_management(
    app_with_user, admin_client
):
    """POST to user_management toggling is_admin fires user_flags_changed hook."""
    from otterwiki.auth import SimpleAuth, db

    # Get the non-admin user id
    other_user = SimpleAuth.User.query.filter_by(
        email="another@user.org"
    ).first()
    assert other_user is not None
    assert other_user.is_admin == False

    recorder = make_recorder()
    try:
        rv = admin_client.post(
            "/-/admin/user_management",
            data={
                "is_approved": [1, other_user.id],
                "is_admin": [1, other_user.id],  # promote other_user to admin
                "allow_read": [other_user.id],
                "allow_write": [other_user.id],
                "allow_upload": [other_user.id],
            },
            follow_redirects=True,
        )
        assert rv.status_code == 200
        flag_calls = [
            c for c in recorder.calls if c[0] == "user_flags_changed"
        ]
        assert len(flag_calls) >= 1
        emails = [c[1]["user_email"] for c in flag_calls]
        assert "another@user.org" in emails
    finally:
        _get_plugin_manager().unregister(recorder)
        # Reset other_user to non-admin state
        other_user = SimpleAuth.User.query.filter_by(
            email="another@user.org"
        ).first()
        if other_user is not None and other_user.is_admin:
            admin_client.post(
                "/-/admin/user_management",
                data={
                    "is_approved": [1, other_user.id],
                    "is_admin": [1],  # exclude other_user from admin list
                    "allow_read": [other_user.id],
                    "allow_write": [other_user.id],
                    "allow_upload": [other_user.id],
                },
                follow_redirects=True,
            )


def test_user_flags_changed_hook_not_fired_when_unchanged(
    app_with_user, admin_client
):
    """POST with same flags does not fire user_flags_changed hook."""
    from otterwiki.auth import SimpleAuth, db

    other_user = SimpleAuth.User.query.filter_by(
        email="another@user.org"
    ).first()
    assert other_user is not None

    # Post with the current state (not changing anything)
    rv = admin_client.post(
        "/-/admin/user_management",
        data={
            "is_approved": (
                [1, other_user.id] if other_user.is_approved else [1]
            ),
            "is_admin": [1],
            "allow_read": [other_user.id] if other_user.allow_read else [],
            "allow_write": [other_user.id] if other_user.allow_write else [],
            "allow_upload": [other_user.id] if other_user.allow_upload else [],
        },
        follow_redirects=True,
    )
    assert rv.status_code == 200

    recorder = make_recorder()
    try:
        # Refresh user to get current state
        other_user = SimpleAuth.User.query.filter_by(
            email="another@user.org"
        ).first()
        # Post the exact same values again
        rv = admin_client.post(
            "/-/admin/user_management",
            data={
                "is_approved": (
                    [1, other_user.id] if other_user.is_approved else [1]
                ),
                "is_admin": [1],
                "allow_read": [other_user.id] if other_user.allow_read else [],
                "allow_write": (
                    [other_user.id] if other_user.allow_write else []
                ),
                "allow_upload": (
                    [other_user.id] if other_user.allow_upload else []
                ),
            },
            follow_redirects=True,
        )
        assert rv.status_code == 200
        flag_calls = [
            c for c in recorder.calls if c[0] == "user_flags_changed"
        ]
        assert len(flag_calls) == 0
    finally:
        _get_plugin_manager().unregister(recorder)


def test_user_flags_changed_hook_fires_from_user_edit(
    app_with_user, admin_client
):
    """POST to /-/user/<uid> toggling allow_write fires user_flags_changed hook."""
    from otterwiki.auth import SimpleAuth, db

    other_user = SimpleAuth.User.query.filter_by(
        email="another@user.org"
    ).first()
    assert other_user is not None

    # Ensure allow_write starts as False
    other_user.allow_write = False
    db.session.commit()

    recorder = make_recorder()
    try:
        rv = admin_client.post(
            f"/-/user/{other_user.id}",
            data={
                "name": other_user.name,
                "email": other_user.email,
                "allow_write": "True",
            },
            follow_redirects=True,
        )
        assert rv.status_code == 200
        flag_calls = [
            c for c in recorder.calls if c[0] == "user_flags_changed"
        ]
        assert len(flag_calls) == 1
        call_data = flag_calls[0][1]
        assert call_data["user_email"] == "another@user.org"
        assert call_data["changes"] is not None
        assert len(call_data["changes"]) > 0
    finally:
        _get_plugin_manager().unregister(recorder)
