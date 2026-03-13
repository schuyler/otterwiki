"""Tests for space↔underscore normalization when TREAT_UNDERSCORE_AS_SPACE_FOR_TITLES is enabled.

When the setting is on:
- Spaces in page paths should be stored as underscores on disk
- URLs should use underscores, not spaces
- Incoming URLs with spaces should redirect to underscore URLs
- WikiLinks with spaces should resolve to underscore files
- Display titles should show spaces (existing behavior)
"""

import pytest


@pytest.fixture
def underscore_app(create_app):
    """App with underscore-as-space and retain-case both enabled."""
    create_app.config["TREAT_UNDERSCORE_AS_SPACE_FOR_TITLES"] = True
    create_app.config["RETAIN_PAGE_NAME_CASE"] = True
    yield create_app


@pytest.fixture
def underscore_client(underscore_app):
    return underscore_app.test_client()


class TestGetFilenameNormalization:
    """get_filename should convert spaces to underscores when the setting is on."""

    def test_spaces_become_underscores(self, underscore_app):
        from otterwiki.helper import get_filename

        assert get_filename("Agent Workflow") == "Agent_Workflow.md"

    def test_nested_spaces_become_underscores(self, underscore_app):
        from otterwiki.helper import get_filename

        assert (
            get_filename("Design/Agent Workflow") == "Design/Agent_Workflow.md"
        )

    def test_existing_underscores_unchanged(self, underscore_app):
        from otterwiki.helper import get_filename

        assert get_filename("Agent_Workflow") == "Agent_Workflow.md"

    def test_no_normalization_when_disabled(self, create_app):
        create_app.config["TREAT_UNDERSCORE_AS_SPACE_FOR_TITLES"] = False
        from otterwiki.helper import get_filename

        assert get_filename("Agent Workflow") == "Agent Workflow.md"


class TestPageCreationWithSpaces:
    """Creating a page with spaces in the name should store with underscores."""

    def test_save_with_spaces_creates_underscore_file(
        self, underscore_client, underscore_app
    ):
        rv = underscore_client.post(
            "/Design/Agent Workflow/save",
            data={
                "content": "# Agent Workflow\n\nTest content.",
                "commit": "create",
            },
            follow_redirects=False,
        )
        # Should redirect after save
        assert rv.status_code in (200, 302)
        # File on disk should have underscores
        assert underscore_app.storage.exists("Design/Agent_Workflow.md")


class TestURLNormalization:
    """URLs with spaces should redirect to underscore equivalents."""

    def _create_page(self, client, path, content="# Test\n\nContent."):
        """Helper to create a page via underscore path."""
        return client.post(
            f"/{path}/save",
            data={"content": content, "commit": "create"},
            follow_redirects=True,
        )

    def test_view_with_underscores_works(self, underscore_client):
        self._create_page(underscore_client, "Test_Page")
        rv = underscore_client.get("/Test_Page")
        assert rv.status_code == 200

    def test_view_with_spaces_redirects_to_underscores(
        self, underscore_client
    ):
        self._create_page(underscore_client, "Test_Page")
        rv = underscore_client.get("/Test Page", follow_redirects=False)
        assert rv.status_code == 302
        assert "Test_Page" in rv.headers["Location"]

    def test_nested_view_with_spaces_redirects(self, underscore_client):
        self._create_page(underscore_client, "Design/Test_Page")
        rv = underscore_client.get("/Design/Test Page", follow_redirects=False)
        assert rv.status_code == 302
        assert "Design/Test_Page" in rv.headers["Location"]

    def test_no_redirect_when_disabled(self, create_app):
        create_app.config["TREAT_UNDERSCORE_AS_SPACE_FOR_TITLES"] = False
        create_app.config["RETAIN_PAGE_NAME_CASE"] = True
        client = create_app.test_client()
        # Create page with space in name
        client.post(
            "/Test Page/save",
            data={"content": "# Test\n\nContent.", "commit": "create"},
            follow_redirects=True,
        )
        rv = client.get("/Test Page", follow_redirects=False)
        # Should NOT redirect — spaces are the real filename
        assert rv.status_code == 200


class TestWikiLinkResolution:
    """WikiLinks with spaces should resolve to underscore files."""

    def _create_page(self, client, path, content="# Test\n\nContent."):
        return client.post(
            f"/{path}/save",
            data={"content": content, "commit": "create"},
            follow_redirects=True,
        )

    def test_wikilink_with_spaces_renders_underscore_href(
        self, underscore_client
    ):
        self._create_page(
            underscore_client, "Target_Page", "# Target\n\nTarget page."
        )
        self._create_page(
            underscore_client,
            "Source_Page",
            "# Source\n\nLink to [[Target Page]].",
        )
        rv = underscore_client.get("/Source_Page")
        html = rv.data.decode()
        # The href should use underscores, NOT raw spaces or %20
        assert 'href="/Target_Page"' in html
        assert 'href="/Target Page"' not in html
        assert 'href="/Target%20Page"' not in html

    def test_wikilink_with_underscores_still_works(self, underscore_client):
        self._create_page(
            underscore_client, "Target_Page", "# Target\n\nTarget page."
        )
        self._create_page(
            underscore_client,
            "Source_Page",
            "# Source\n\nLink to [[Target_Page]].",
        )
        rv = underscore_client.get("/Source_Page")
        html = rv.data.decode()
        assert 'href="/Target_Page"' in html


class TestPageIndexURLs:
    """Page index should generate URLs with underscores."""

    def test_page_index_uses_underscores(self, underscore_client):
        underscore_client.post(
            "/My_Test_Page/save",
            data={"content": "# My Test Page\n\nContent.", "commit": "create"},
            follow_redirects=True,
        )
        rv = underscore_client.get("/-/index")
        html = rv.data.decode()
        # Index links should use underscores in URLs
        assert "/My_Test_Page" in html
        # Display text should show spaces
        assert "My Test Page" in html


class TestNonViewRouteRedirects:
    """Non-view routes (edit, history, etc.) should also redirect spaces."""

    def _create_page(self, client, path, content="# Test\n\nContent."):
        return client.post(
            f"/{path}/save",
            data={"content": content, "commit": "create"},
            follow_redirects=True,
        )

    def test_edit_with_spaces_redirects(self, underscore_client):
        self._create_page(underscore_client, "Test_Page")
        rv = underscore_client.get("/Test Page/edit", follow_redirects=False)
        assert rv.status_code == 302
        assert "Test_Page/edit" in rv.headers["Location"]

    def test_history_with_spaces_redirects(self, underscore_client):
        self._create_page(underscore_client, "Test_Page")
        rv = underscore_client.get(
            "/Test Page/history", follow_redirects=False
        )
        assert rv.status_code == 302
        assert "Test_Page/history" in rv.headers["Location"]


class TestCaseInsensitiveWithUnderscores:
    """RETAIN_PAGE_NAME_CASE=False + TREAT_UNDERSCORE_AS_SPACE_FOR_TITLES=True."""

    @pytest.fixture
    def lowercase_underscore_app(self, create_app):
        create_app.config["TREAT_UNDERSCORE_AS_SPACE_FOR_TITLES"] = True
        create_app.config["RETAIN_PAGE_NAME_CASE"] = False
        yield create_app

    @pytest.fixture
    def lowercase_underscore_client(self, lowercase_underscore_app):
        return lowercase_underscore_app.test_client()

    def test_file_stored_lowercase_with_underscores(
        self, lowercase_underscore_client, lowercase_underscore_app
    ):
        lowercase_underscore_client.post(
            "/Design/Agent Workflow/save",
            data={
                "content": "# Agent Workflow\n\nContent.",
                "commit": "create",
            },
            follow_redirects=True,
        )
        assert lowercase_underscore_app.storage.exists(
            "design/agent_workflow.md"
        )

    def test_redirect_lowercases_and_underscores(
        self, lowercase_underscore_client
    ):
        lowercase_underscore_client.post(
            "/design/agent_workflow/save",
            data={
                "content": "# Agent Workflow\n\nContent.",
                "commit": "create",
            },
            follow_redirects=True,
        )
        rv = lowercase_underscore_client.get(
            "/Design/Agent Workflow", follow_redirects=False
        )
        assert rv.status_code == 302
        assert "Agent_Workflow" in rv.headers["Location"]


class TestBreadcrumbURLs:
    """Breadcrumbs should use underscore URLs."""

    def test_breadcrumbs_use_underscores(self, underscore_client):
        underscore_client.post(
            "/My_Folder/My_Page/save",
            data={"content": "# My Page\n\nContent.", "commit": "create"},
            follow_redirects=True,
        )
        rv = underscore_client.get("/My_Folder/My_Page")
        html = rv.data.decode()
        # Breadcrumb links should have underscores
        assert "/My_Folder" in html
