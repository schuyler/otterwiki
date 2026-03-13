#!/usr/bin/env python
"""
otterwiki.lambda_handler

AWS Lambda handler for Otterwiki using Mangum.

Mangum adapts WSGI/ASGI applications for AWS Lambda behind API Gateway
or ALB. This module provides the Lambda entry point while keeping
Otterwiki's existing Flask initialization path unchanged.

Usage:
    Set the Lambda handler to: otterwiki.lambda_handler.handler

Configuration:
    All standard Otterwiki configuration applies. Set OTTERWIKI_SETTINGS
    to point to a config file on EFS, or configure via environment
    variables (REPOSITORY, SECRET_KEY, SQLALCHEMY_DATABASE_URI, etc.).

    MANGUM_LOG_LEVEL: Set Mangum's log level (default: "WARNING").

EFS requirements:
    The following must reside on a persistent filesystem (EFS):
    - Git repository (REPOSITORY path)
    - SQLite database (SQLALCHEMY_DATABASE_URI path)
    - Settings config file (OTTERWIKI_SETTINGS path, if used)

    The following are bundled with the package and need no EFS:
    - Static assets (otterwiki/static/)
    - Templates (otterwiki/templates/)
    - initial_home.md

    The following are ephemeral and fine on Lambda's /tmp:
    - SSH key tempfiles (repomgmt.py, only used for git remote ops)

    Flask sessions are cookie-based (signed with SECRET_KEY) and
    require no server-side storage.
"""

import os
import logging

try:
    from mangum import Mangum
except ImportError:
    Mangum = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# Only build the handler if Mangum is available. This allows the module
# to be imported safely in environments where Mangum is not installed,
# which is important because pyproject.toml lists it as optional.
if Mangum is not None:
    from otterwiki.server import app

    log_level = os.environ.get("MANGUM_LOG_LEVEL", "WARNING")
    handler = Mangum(app, lifespan="off", log_level=log_level)
else:

    def handler(event, context):  # type: ignore[misc]
        raise RuntimeError(
            "Mangum is not installed. Install it with: pip install mangum"
        )
