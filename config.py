"""
config.py

Central configuration for the MovieStream application.

Two configs are provided:
    - DevelopmentConfig: SQLite, debug on, used for local development.
    - ProductionConfig:  PostgreSQL, debug off, used for deployment.

The active config is selected via the FLASK_ENV environment variable.
Secrets (SECRET_KEY, DATABASE_URL) are read from environment variables
so they are never hard-coded into source control.
"""

import os
from datetime import timedelta

# Absolute path to the project root, used to build the SQLite file path.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    """Settings shared by every environment."""

    # Flask-WTF / session security
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    WTF_CSRF_ENABLED = True
    # Tokens stay valid for the whole session instead of expiring after
    # an hour, so a long-open page's JS (favorites, ratings) keeps working.
    WTF_CSRF_TIME_LIMIT = None

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File uploads. Movie/trailer files live OUTSIDE static/ on purpose:
    # anything under static/ is served by Flask with zero
    # authentication, which would make every video publicly reachable
    # at a guessable URL regardless of login. Posters stay in static/
    # since a thumbnail image isn't sensitive; the actual video files
    # are only ever served through the login-gated /watch/... routes
    # in blueprints/movies/routes.py (see stream_video/stream_trailer/
    # download_movie).
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_SIZE_GB", 20)) * 1024 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    POSTER_FOLDER = os.path.join(BASE_DIR, "static", "posters")
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")
    MOVIE_FOLDER = os.path.join(MEDIA_ROOT, "movies")
    AVATAR_FOLDER = os.path.join(BASE_DIR, "static", "avatars")
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "mov", "mkv"}
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # Session / login
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(BaseConfig):
    """Local development: SQLite, verbose errors."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DEV_DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'moviestream.db')}",
    )


class ProductionConfig(BaseConfig):
    """Production: PostgreSQL, secure cookies, debug off."""

    DEBUG = False
    # No fallback: create_app() refuses to start without a real key.
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/moviestream"
    )
    SESSION_COOKIE_SECURE = True


# Maps the FLASK_ENV value to the config class that should be loaded.
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    """Return the config class matching FLASK_ENV (defaults to development)."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
