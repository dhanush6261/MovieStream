"""
Defines the 'main' blueprint: the public-facing catalog pages
(home page, and later movie detail / browse / search pages).

The Blueprint object is created here, separate from routes.py, so
routes.py can `from blueprints.main import main_bp` without a
circular import back to this file.
"""

from flask import Blueprint

main_bp = Blueprint(
    "main",
    __name__,
    template_folder="../../templates/main",
)

# Import at the bottom so route functions attach to main_bp above
# without creating a circular import at module load time.
from blueprints.main import routes  # noqa: E402,F401
