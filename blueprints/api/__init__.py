"""
Defines the 'api' blueprint: JSON REST endpoints under /api for
movies, genres, languages, search, upload, and library scanning.
Consumed by the frontend's api.js / search.js / player.js instead of
full page reloads.
"""

from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from blueprints.api import routes  # noqa: E402,F401
