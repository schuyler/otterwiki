#!/usr/bin/env python
# vim: set et ts=8 sts=4 sw=4 ai:

"""Tests for PLATFORM_MODE admin panel hiding (P2-8)."""

from bs4 import BeautifulSoup


# Routes that should be disabled in platform mode
DISABLED_ROUTES = [
    "/-/admin/repository_management",
    "/-/admin/user_management",
    "/-/admin/permissions_and_registration",
    "/-/admin/mail_preferences",
]

# Routes that should remain enabled in platform mode
ENABLED_ROUTES = [
    "/-/admin",
    "/-/admin/sidebar_preferences",
    "/-/admin/content_and_editing",
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
            for route in DISABLED_ROUTES:
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
            for route in DISABLED_ROUTES:
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
            assert "Repository Management" not in nav_text
            assert "User Management" not in nav_text
            assert "Permissions and Registration" not in nav_text
            assert "Mail Preferences" not in nav_text
            # These should still be visible
            assert "Application Preferences" in nav_text
            assert "Sidebar Preferences" in nav_text
            assert "Content and Editing" in nav_text
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_user_edit_route_returns_404(self, app_with_user, admin_client):
        """The /-/user/ route should return 404 in platform mode."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get("/-/user/")
            assert rv.status_code == 404
        finally:
            app_with_user.config["PLATFORM_MODE"] = False
