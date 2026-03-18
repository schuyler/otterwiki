#!/usr/bin/env python
# vim: set et ts=8 sts=4 sw=4 ai:

"""Tests for PLATFORM_MODE admin panel hiding (P2-8) and permissions panel."""

from unittest.mock import patch

from bs4 import BeautifulSoup


# Routes that should be disabled in platform mode (return 200 when enabled)
DISABLED_ROUTES = [
    "/-/admin/mail_preferences",
    "/-/admin/repository_management",
]

# Routes that should be disabled in platform mode but don't return 200 when enabled
# (e.g., they require valid inputs/hashes to succeed)
DISABLED_WEBHOOK_ROUTES = [
    "/-/api/v1/pull/deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
]

# Routes that should remain enabled in platform mode
ENABLED_ROUTES = [
    "/-/admin",
    "/-/admin/sidebar_preferences",
    "/-/admin/content_and_editing",
    "/-/admin/permissions_and_registration",
    "/-/admin/user_management",
]


class TestPlatformModeDisabled:
    """Tests with PLATFORM_MODE=False (default) — everything should work."""

    def test_disabled_routes_accessible(self, admin_client):
        """All admin routes should be accessible when PLATFORM_MODE is off."""
        for route in DISABLED_ROUTES:
            rv = admin_client.get(route)
            assert rv.status_code == 200, f"{route} should return 200"

    def test_enabled_routes_accessible(self, admin_client):
        """Enabled admin routes should be accessible when PLATFORM_MODE is off."""
        for route in ENABLED_ROUTES:
            rv = admin_client.get(route)
            assert rv.status_code == 200, f"{route} should return 200"

    def test_nav_shows_all_sections(self, admin_client):
        """All nav items should be visible when PLATFORM_MODE is off."""
        rv = admin_client.get("/-/admin")
        html = rv.data.decode()
        soup = BeautifulSoup(html, "html.parser")
        nav_text = soup.get_text()
        assert "Repository Management" in nav_text
        assert "User Management" in nav_text
        assert "Permissions and Registration" in nav_text
        assert "Mail Preferences" in nav_text
        assert "Application Preferences" in nav_text
        assert "Sidebar Preferences" in nav_text
        assert "Content and Editing" in nav_text


class TestPlatformModeEnabled:
    """Tests with PLATFORM_MODE=True — disabled sections hidden, routes return 404."""

    def test_disabled_routes_return_404(self, app_with_user, admin_client):
        """Disabled admin routes should return 404 in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            for route in DISABLED_ROUTES + DISABLED_WEBHOOK_ROUTES:
                rv = admin_client.get(route)
                assert rv.status_code == 404, f"{route} should return 404"
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_disabled_routes_post_returns_404(
        self, app_with_user, admin_client
    ):
        """POST to disabled admin routes should also return 404 in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            for route in DISABLED_ROUTES + DISABLED_WEBHOOK_ROUTES:
                rv = admin_client.post(route, data={})
                assert rv.status_code == 404, f"POST {route} should return 404"
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_enabled_routes_still_accessible(
        self, app_with_user, admin_client
    ):
        """Enabled admin routes should still work in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            for route in ENABLED_ROUTES:
                rv = admin_client.get(route)
                assert rv.status_code == 200, f"{route} should return 200"
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_nav_hides_disabled_sections(self, app_with_user, admin_client):
        """Disabled nav items should be hidden in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/admin")
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            nav_text = soup.get_text()
            # These should be hidden
            assert "Mail Preferences" not in nav_text
            assert "Repository Management" not in nav_text
            # These should still be visible
            assert "Application Preferences" in nav_text
            assert "Sidebar Preferences" in nav_text
            assert "Content and Editing" in nav_text
            assert "Permissions and Registration" in nav_text
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_user_edit_route_accessible(self, app_with_user, admin_client):
        """The /-/user/ route should be accessible in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/user/")
            assert rv.status_code == 200
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_permissions_nav_visible_in_platform_mode(
        self, app_with_user, admin_client
    ):
        """Permissions and Registration nav link should be visible in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/admin")
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            nav_text = soup.get_text()
            assert "Permissions and Registration" in nav_text
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_permissions_route_accessible_in_platform_mode(
        self, app_with_user, admin_client
    ):
        """GET /-/admin/permissions_and_registration should return 200 in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/admin/permissions_and_registration")
            assert rv.status_code == 200
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_registration_fields_not_saved_in_platform_mode(
        self, app_with_user, admin_client
    ):
        """Registration checkboxes must not be persisted when PLATFORM_MODE=True."""
        from otterwiki.server import db, Preferences

        # Save original access settings to restore after test (avoid test state pollution)
        orig_read = app_with_user.config.get("READ_ACCESS", "ANONYMOUS")
        orig_write = app_with_user.config.get("WRITE_ACCESS", "ANONYMOUS")
        orig_attachment = app_with_user.config.get(
            "ATTACHMENT_ACCESS", "ANONYMOUS"
        )
        # Set known baseline
        app_with_user.config["DISABLE_REGISTRATION"] = False
        app_with_user.config["AUTO_APPROVAL"] = False
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.post(
                "/-/admin/permissions_and_registration",
                data={
                    "READ_access": "ANONYMOUS",
                    "WRITE_access": "REGISTERED",
                    "ATTACHMENT_access": "APPROVED",
                    "disable_registration": "True",
                    "auto_approval": "True",
                    "email_needs_confirmation": "True",
                    "notify_admins_on_register": "True",
                    "notify_user_on_approval": "True",
                },
                follow_redirects=True,
            )
            assert rv.status_code == 200
            # Access settings should be updated
            assert app_with_user.config["READ_ACCESS"] == "ANONYMOUS"
            assert app_with_user.config["WRITE_ACCESS"] == "REGISTERED"
            # Registration fields must NOT have been saved
            assert app_with_user.config["DISABLE_REGISTRATION"] == False
            assert app_with_user.config["AUTO_APPROVAL"] == False
        finally:
            app_with_user.config["PLATFORM_MODE"] = False
            # Restore access settings in both app.config and DB to avoid polluting
            # subsequent tests (the DB persists across tests via shared in-memory SQLite)
            for name, value in [
                ("READ_ACCESS", orig_read),
                ("WRITE_ACCESS", orig_write),
                ("ATTACHMENT_ACCESS", orig_attachment),
            ]:
                app_with_user.config[name] = value
                entry = Preferences.query.filter_by(name=name).first()
                if entry is not None:
                    db.session.delete(entry)
            db.session.commit()


class TestDashboardNavigation:
    """Tests for Dashboard link in wiki dropdown in PLATFORM_MODE."""

    def test_dashboard_link_shown_in_platform_mode(
        self, app_with_user, admin_client
    ):
        """Dashboard link should appear in the wiki dropdown when PLATFORM_MODE=True."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/Home", follow_redirects=True)
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            links = soup.find_all("a", href=lambda h: h and "/app/" in h)
            assert any(
                "Dashboard" in link.get_text() for link in links
            ), "Dashboard link should be present in platform mode"
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_dashboard_link_hidden_without_platform_mode(
        self, app_with_user, admin_client
    ):
        """Dashboard link should not appear when PLATFORM_MODE=False."""
        app_with_user.config["PLATFORM_MODE"] = False
        rv = admin_client.get("/Home", follow_redirects=True)
        html = rv.data.decode()
        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=lambda h: h and "/app/" in h)
        assert not any(
            "Dashboard" in link.get_text() for link in links
        ), "Dashboard link should not be present when PLATFORM_MODE=False"

    def test_dashboard_link_points_to_platform_domain(
        self, app_with_user, admin_client, monkeypatch
    ):
        """Dashboard link href should use PLATFORM_DOMAIN env var when set."""
        monkeypatch.setenv("PLATFORM_DOMAIN", "test.example.com")
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/Home", follow_redirects=True)
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            links = soup.find_all(
                "a", href=lambda h: h and "test.example.com/app/" in h
            )
            assert (
                len(links) > 0
            ), "Dashboard link should point to https://test.example.com/app/"
        finally:
            app_with_user.config["PLATFORM_MODE"] = False


class TestPlatformModeRepomgmt:
    """Tests that repomgmt operations are suppressed in PLATFORM_MODE."""

    def test_auto_push_disabled_in_platform_mode(self, app_with_user):
        """auto_push_if_enabled() must not attempt a push when PLATFORM_MODE=True."""
        from otterwiki.repomgmt import RepositoryManager

        app_with_user.config["PLATFORM_MODE"] = True
        app_with_user.config["GIT_REMOTE_PUSH_ENABLED"] = True
        app_with_user.config["GIT_REMOTE_PUSH_URL"] = (
            "git@github.com:example/repo.git"
        )
        try:
            rm = RepositoryManager(app_with_user.storage)
            with patch.object(rm, "push_to_remote_async") as mock_push:
                rm.auto_push_if_enabled()
                mock_push.assert_not_called()
        finally:
            app_with_user.config["PLATFORM_MODE"] = False
            app_with_user.config["GIT_REMOTE_PUSH_ENABLED"] = False
            app_with_user.config["GIT_REMOTE_PUSH_URL"] = None

    def test_auto_pull_webhook_disabled_in_platform_mode(self, app_with_user):
        """auto_pull_webhook() must return False and not attempt a pull when PLATFORM_MODE=True."""
        from otterwiki.repomgmt import RepositoryManager

        app_with_user.config["PLATFORM_MODE"] = True
        app_with_user.config["GIT_REMOTE_PULL_ENABLED"] = True
        app_with_user.config["GIT_REMOTE_PULL_URL"] = (
            "git@github.com:example/repo.git"
        )
        try:
            rm = RepositoryManager(app_with_user.storage)
            with patch.object(rm, "pull_from_remote_async") as mock_pull:
                result = rm.auto_pull_webhook()
                assert result is False
                mock_pull.assert_not_called()
        finally:
            app_with_user.config["PLATFORM_MODE"] = False
            app_with_user.config["GIT_REMOTE_PULL_ENABLED"] = False
            app_with_user.config["GIT_REMOTE_PULL_URL"] = None
