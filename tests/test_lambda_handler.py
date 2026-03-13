#!/usr/bin/env python
"""
Tests for otterwiki.lambda_handler

Tests that:
- The module imports without error whether apig-wsgi is installed or not
- The handler wraps the Flask app correctly when apig-wsgi is available
- The handler raises RuntimeError when apig-wsgi is not installed
- Otterwiki initializes correctly through the handler path
"""

import importlib
import os
import sys
import types
from unittest import mock

import pytest

import otterwiki.gitstorage


@pytest.fixture
def configured_env(tmpdir):
    """Set up a minimal Otterwiki environment for handler tests."""
    tmpdir.mkdir("repo")
    storage = otterwiki.gitstorage.GitStorage(
        path=str(tmpdir.join("repo")), initialize=True
    )
    settings_cfg = str(tmpdir.join("settings.cfg"))
    with open(settings_cfg, "w") as f:
        f.writelines(
            [
                "REPOSITORY = '{}'\n".format(str(storage.path)),
                "SITE_NAME = 'TEST WIKI'\n",
                "DEBUG = True\n",
                "TESTING = True\n",
                "SECRET_KEY = 'Testing Testing Testing'\n",
            ]
        )
    os.environ["OTTERWIKI_SETTINGS"] = settings_cfg
    yield {
        "settings_cfg": settings_cfg,
        "repo_path": str(storage.path),
    }


def test_import_without_apig_wsgi(configured_env):
    """When apig-wsgi is not installed, the module should still import."""
    # Temporarily hide apig_wsgi from the import system
    original = sys.modules.get("apig_wsgi")
    sys.modules["apig_wsgi"] = None  # type: ignore[assignment]
    try:
        # Force reimport
        if "otterwiki.lambda_handler" in sys.modules:
            del sys.modules["otterwiki.lambda_handler"]
        import otterwiki.lambda_handler

        importlib.reload(otterwiki.lambda_handler)

        # Handler should exist but raise RuntimeError
        with pytest.raises(RuntimeError, match="apig-wsgi is not installed"):
            otterwiki.lambda_handler.handler({}, None)
    finally:
        if original is not None:
            sys.modules["apig_wsgi"] = original
        else:
            sys.modules.pop("apig_wsgi", None)
        # Clean up
        if "otterwiki.lambda_handler" in sys.modules:
            del sys.modules["otterwiki.lambda_handler"]


def test_import_with_apig_wsgi_mock(configured_env):
    """When apig-wsgi is installed, handler should be created via make_lambda_handler."""
    # Create a mock apig_wsgi module
    mock_apig_wsgi_module = types.ModuleType("apig_wsgi")
    mock_handler = mock.MagicMock(name="lambda_handler")
    mock_make = mock.MagicMock(
        name="make_lambda_handler", return_value=mock_handler
    )
    mock_apig_wsgi_module.make_lambda_handler = mock_make  # type: ignore[attr-defined]

    original = sys.modules.get("apig_wsgi")
    sys.modules["apig_wsgi"] = mock_apig_wsgi_module
    try:
        if "otterwiki.lambda_handler" in sys.modules:
            del sys.modules["otterwiki.lambda_handler"]
        import otterwiki.lambda_handler

        importlib.reload(otterwiki.lambda_handler)

        # make_lambda_handler should have been called with the Flask app
        # (may be called more than once due to import + reload)
        assert mock_make.call_count >= 1
        call_args = mock_make.call_args
        # First positional arg should be the Flask app
        from otterwiki.server import app

        assert call_args[0][0] is app
    finally:
        if original is not None:
            sys.modules["apig_wsgi"] = original
        else:
            sys.modules.pop("apig_wsgi", None)
        if "otterwiki.lambda_handler" in sys.modules:
            del sys.modules["otterwiki.lambda_handler"]


def test_handler_invocation_with_apig_wsgi(configured_env):
    """Test that the handler can be invoked with a mock Lambda event."""
    mock_apig_wsgi_module = types.ModuleType("apig_wsgi")

    call_log = []

    def fake_make_lambda_handler(app):
        def fake_handler(event, context):
            call_log.append((event, context))
            return {"statusCode": 200, "body": "ok"}

        return fake_handler

    mock_apig_wsgi_module.make_lambda_handler = fake_make_lambda_handler  # type: ignore[attr-defined]

    original = sys.modules.get("apig_wsgi")
    sys.modules["apig_wsgi"] = mock_apig_wsgi_module
    try:
        if "otterwiki.lambda_handler" in sys.modules:
            del sys.modules["otterwiki.lambda_handler"]
        import otterwiki.lambda_handler

        importlib.reload(otterwiki.lambda_handler)

        event = {"httpMethod": "GET", "path": "/"}
        context = mock.MagicMock()
        result = otterwiki.lambda_handler.handler(event, context)

        assert result["statusCode"] == 200
        assert len(call_log) == 1
        assert call_log[0][0] is event
    finally:
        if original is not None:
            sys.modules["apig_wsgi"] = original
        else:
            sys.modules.pop("apig_wsgi", None)
        if "otterwiki.lambda_handler" in sys.modules:
            del sys.modules["otterwiki.lambda_handler"]


def test_flask_app_initializes_for_lambda(configured_env):
    """Verify the Flask app initializes correctly through the lambda path."""
    from otterwiki.server import app

    assert app is not None
    # The app is a module-level singleton; SITE_NAME is set from the
    # first OTTERWIKI_SETTINGS loaded during this test session.
    assert app.config["SITE_NAME"] == "TEST WIKI"
    # REPOSITORY will point to whichever tmpdir was active when the
    # server module was first imported. Just verify it's set and valid.
    assert app.config["REPOSITORY"] is not None
    assert os.path.isdir(app.config["REPOSITORY"])
