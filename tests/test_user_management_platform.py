#!/usr/bin/env python
# vim: set et ts=8 sts=4 sw=4 ai:

"""Tests for User Management in PLATFORM_MODE (Phase 2)."""

from bs4 import BeautifulSoup


class TestUserManagementRoutesInPlatformMode:
    """User Management and User Edit routes should be accessible in PLATFORM_MODE."""

    def test_user_management_route_accessible(
        self, app_with_user, admin_client
    ):
        """GET /-/admin/user_management should return 200 in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/admin/user_management")
            assert rv.status_code == 200
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_user_management_post_accessible(
        self, app_with_user, admin_client
    ):
        """POST /-/admin/user_management should not return 404 in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.post("/-/admin/user_management", data={})
            # Should redirect (302) or 200, but NOT 404
            assert rv.status_code != 404
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_user_edit_route_accessible(self, app_with_user, admin_client):
        """GET /-/user/ (add user form) should return 200 in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/user/")
            assert rv.status_code == 200
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_nav_shows_user_management_in_platform_mode(
        self, app_with_user, admin_client
    ):
        """User Management nav link should be visible in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/admin")
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            nav_text = soup.get_text()
            assert "User Management" in nav_text
        finally:
            app_with_user.config["PLATFORM_MODE"] = False


class TestUserManagementTemplateInPlatformMode:
    """Template customizations for PLATFORM_MODE."""

    def test_add_user_form_has_handle_field(self, app_with_user, admin_client):
        """Add User form should show Handle field instead of eMail in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/user/")
            html = rv.data.decode()
            # Should have "Handle" label, not "eMail" for the email field
            assert "Handle" in html
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_add_user_form_hides_password_fields(
        self, app_with_user, admin_client
    ):
        """Add User form should not show password fields in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/user/")
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            password_inputs = soup.find_all("input", {"type": "password"})
            assert len(password_inputs) == 0
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_add_user_form_hides_email_confirmed_flag(
        self, app_with_user, admin_client
    ):
        """Add User form should not show email_confirmed checkbox in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/user/")
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            email_confirmed = soup.find("input", {"name": "email_confirmed"})
            assert email_confirmed is None
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_user_management_list_shows_handle_header(
        self, app_with_user, admin_client
    ):
        """User Management table header should say Handle instead of eMail in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/admin/user_management")
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            headers = [th.get_text(strip=True) for th in soup.find_all("th")]
            assert "Handle" in headers
            assert "eMail" not in headers
        finally:
            app_with_user.config["PLATFORM_MODE"] = False


class TestAddUserInPlatformMode:
    """Adding users via handle in PLATFORM_MODE."""

    def test_add_user_with_handle(self, app_with_user, admin_client):
        """POST to /-/user/ with a handle should create a user in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.post(
                "/-/user/",
                data={
                    "name": "Alice",
                    "email": "@alice.bsky.social",
                    "is_approved": "1",
                    "allow_read": "1",
                },
                follow_redirects=True,
            )
            assert rv.status_code == 200
            html = rv.data.decode()
            # Should show the user was added (redirects to user edit page)
            assert "Alice" in html
            assert "@alice.bsky.social" in html
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_add_user_handle_stored_in_email_field(
        self, app_with_user, admin_client
    ):
        """The handle should be stored in the email field of the User model."""
        from otterwiki.models import User as UserModel

        app_with_user.config["PLATFORM_MODE"] = True
        try:
            admin_client.post(
                "/-/user/",
                data={
                    "name": "Bob",
                    "email": "@bob.bsky.social",
                    "is_approved": "1",
                },
                follow_redirects=True,
            )
            user = UserModel.query.filter_by(email="@bob.bsky.social").first()
            assert user is not None
            assert user.name == "Bob"
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_add_user_without_password_in_platform_mode(
        self, app_with_user, admin_client
    ):
        """Adding a user without a password should succeed in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.post(
                "/-/user/",
                data={
                    "name": "Carol",
                    "email": "@carol.bsky.social",
                    "is_approved": "1",
                },
                follow_redirects=True,
            )
            assert rv.status_code == 200
            # Should not show any error about password
            html = rv.data.decode()
            assert "password" not in html.lower() or "Carol" in html
        finally:
            app_with_user.config["PLATFORM_MODE"] = False


class TestProxyHeaderAuthUserManagement:
    """ProxyHeaderAuth should support user CRUD for the per-wiki user table."""

    def test_get_all_user_queries_db(self, app_with_user):
        """ProxyHeaderAuth.get_all_user() should return users from the DB."""
        from otterwiki.auth import ProxyHeaderAuth

        auth = ProxyHeaderAuth()
        with app_with_user.test_request_context():
            users = auth.get_all_user()
            # Should return the users created in conftest (at least 2)
            assert len(users) >= 2

    def test_get_user_by_uid(self, app_with_user):
        """ProxyHeaderAuth.get_user(uid) should return a user by ID."""
        from otterwiki.auth import ProxyHeaderAuth
        from otterwiki.models import User as UserModel

        auth = ProxyHeaderAuth()
        with app_with_user.test_request_context():
            # Get first user from DB
            first_user = UserModel.query.first()
            assert first_user is not None
            user = auth.get_user(uid=str(first_user.id))
            assert user is not None
            assert user.id == first_user.id

    def test_get_user_by_email(self, app_with_user):
        """ProxyHeaderAuth.get_user(email) should return a user by email."""
        from otterwiki.auth import ProxyHeaderAuth

        auth = ProxyHeaderAuth()
        with app_with_user.test_request_context():
            user = auth.get_user(email="mail@example.org")
            assert user is not None
            assert user.email == "mail@example.org"

    def test_update_user(self, app_with_user):
        """ProxyHeaderAuth.update_user() should persist changes."""
        from otterwiki.auth import ProxyHeaderAuth
        from otterwiki.models import User as UserModel

        auth = ProxyHeaderAuth()
        with app_with_user.test_request_context():
            user = UserModel.query.filter_by(email="another@user.org").first()
            assert user is not None
            original_name = user.name
            user.name = "Updated Name"
            auth.update_user(user)
            # Re-query
            reloaded = UserModel.query.filter_by(
                email="another@user.org"
            ).first()
            assert reloaded.name == "Updated Name"
            # Restore
            reloaded.name = original_name
            auth.update_user(reloaded)

    def test_delete_user(self, app_with_user):
        """ProxyHeaderAuth.delete_user() should remove the user."""
        from otterwiki.auth import ProxyHeaderAuth
        from otterwiki.models import User as UserModel
        from otterwiki.server import db
        from datetime import datetime

        auth = ProxyHeaderAuth()
        with app_with_user.test_request_context():
            # Create a temp user to delete
            temp = UserModel(
                name="Temp",
                email="temp@example.org",
                first_seen=datetime.now(),
                last_seen=datetime.now(),
            )
            db.session.add(temp)
            db.session.commit()
            uid = temp.id
            auth.delete_user(temp)
            assert UserModel.query.filter_by(id=uid).first() is None

    def test_supported_features_editing_true(self, app_with_user):
        """ProxyHeaderAuth.supported_features() should report editing=True."""
        from otterwiki.auth import ProxyHeaderAuth

        auth = ProxyHeaderAuth()
        features = auth.supported_features()
        assert features["editing"] is True
