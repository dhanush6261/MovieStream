"""
Defines the 'auth' blueprint: register, login, logout, and profile
pages. Kept separate from 'main' since it owns its own forms, its own
Flask-Login wiring, and will grow its own concerns (password reset,
email verification) independently of the public catalog.
"""

from flask import Blueprint

auth_bp = Blueprint(
    "auth",
    __name__,
    template_folder="../../templates/auth",
)

from blueprints.auth import routes  # noqa: E402,F401
