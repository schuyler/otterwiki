#!/usr/bin/env python
# vim: set et ts=8 sts=4 sw=4 ai:

"""Tests for the git-access toggle (/-/admin/git_access) in PLATFORM_MODE."""

import pytest
from bs4 import BeautifulSoup

ADMIN_GIT_ACCESS_URL = "/-/admin/git_access"


class TestGitAccessGET:
    """GET /-/admin/git_access in PLATFORM_MODE with an ADMIN user."""

    def test_get_returns_200_and_toggle(self, app_with_user, admin_client):
        """PLATFORM_MODE + ADMIN: GET returns 200 and renders the git_web_server checkbox."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.get(ADMIN_GIT_ACCESS_URL)
            assert rv.status_code == 200
            html = rv.data.decode()
            soup = BeautifulSoup(html, "html.parser")
            checkbox = soup.find("input", {"name": "git_web_server"})
            assert (
                checkbox is not None
            ), "git_web_server checkbox must be present"
            assert "Enable Git Web server" in html
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_get_non_platform_mode_still_works(self, admin_client):
        """Route is not gated by platform_mode_disabled; it must work without PLATFORM_MODE too."""
        rv = admin_client.get(ADMIN_GIT_ACCESS_URL)
        assert rv.status_code == 200

    def test_get_non_admin_returns_403(self, app_with_user, other_client):
        """Non-ADMIN user (READ/WRITE role) must get 403."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = other_client.get(ADMIN_GIT_ACCESS_URL)
            assert rv.status_code == 403
        finally:
            app_with_user.config["PLATFORM_MODE"] = False


class TestGitAccessPOST:
    """POST /-/admin/git_access."""

    def _pre_seed_remote_prefs(self, admin_client, app_with_user):
        """Pre-seed GIT_REMOTE_PUSH_ENABLED and GIT_REMOTE_PULL_ENABLED to True
        via the repository_management route so we have values to verify aren't clobbered.
        """
        admin_client.post(
            "/-/admin/repository_management",
            data={
                "git_remote_push_enabled": "True",
                "git_remote_push_url": "git@github.com:test/repo.git",
                "git_remote_pull_enabled": "True",
                "git_remote_pull_url": "git@github.com:test/repo.git",
                "update_preferences": "true",
            },
            follow_redirects=True,
        )
        # Verify pre-seed worked
        assert app_with_user.config.get("GIT_REMOTE_PUSH_ENABLED") is True
        assert app_with_user.config.get("GIT_REMOTE_PULL_ENABLED") is True

    def test_post_enable_sets_git_web_server(
        self, app_with_user, admin_client
    ):
        """POST git_web_server=True sets GIT_WEB_SERVER True in app.config."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.post(
                ADMIN_GIT_ACCESS_URL,
                data={"git_web_server": "True"},
                follow_redirects=True,
            )
            assert rv.status_code == 200
            assert app_with_user.config.get("GIT_WEB_SERVER") is True
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_post_does_not_clobber_remote_prefs(
        self, app_with_user, admin_client
    ):
        """POST to git_access MUST NOT touch GIT_REMOTE_PUSH_ENABLED or GIT_REMOTE_PULL_ENABLED."""
        # Pre-seed remote prefs (PLATFORM_MODE off so repo_management route works)
        self._pre_seed_remote_prefs(admin_client, app_with_user)

        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = admin_client.post(
                ADMIN_GIT_ACCESS_URL,
                data={"git_web_server": "True"},
                follow_redirects=True,
            )
            assert rv.status_code == 200
            assert app_with_user.config.get("GIT_WEB_SERVER") is True
            # Remote prefs must survive the git_access POST
            assert (
                app_with_user.config.get("GIT_REMOTE_PUSH_ENABLED") is True
            ), "GIT_REMOTE_PUSH_ENABLED was clobbered by git_access POST"
            assert (
                app_with_user.config.get("GIT_REMOTE_PULL_ENABLED") is True
            ), "GIT_REMOTE_PULL_ENABLED was clobbered by git_access POST"
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_post_disable_sets_git_web_server_false(
        self, app_with_user, admin_client
    ):
        """POST without git_web_server (absent key) sets GIT_WEB_SERVER False."""
        app_with_user.config["PLATFORM_MODE"] = True
        # First enable it
        admin_client.post(
            ADMIN_GIT_ACCESS_URL,
            data={"git_web_server": "True"},
            follow_redirects=True,
        )
        assert app_with_user.config.get("GIT_WEB_SERVER") is True

        try:
            # Now post without git_web_server (checkbox unchecked → key absent)
            rv = admin_client.post(
                ADMIN_GIT_ACCESS_URL,
                data={},
                follow_redirects=True,
            )
            assert rv.status_code == 200
            assert app_with_user.config.get("GIT_WEB_SERVER") is False
        finally:
            app_with_user.config["PLATFORM_MODE"] = False

    def test_post_non_admin_returns_403(self, app_with_user, other_client):
        """Non-ADMIN user gets 403 on POST."""
        app_with_user.config["PLATFORM_MODE"] = True
        try:
            rv = other_client.post(
                ADMIN_GIT_ACCESS_URL,
                data={"git_web_server": "True"},
            )
            assert rv.status_code == 403
        finally:
            app_with_user.config["PLATFORM_MODE"] = False
