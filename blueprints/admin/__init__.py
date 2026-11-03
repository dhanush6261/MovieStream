"""
Defines the 'admin' blueprint: dashboard, movie/category/user
management. Every route in this blueprint is protected by
@admin_required (see decorators.py) -- there is no route here a
non-admin can reach.
"""

from flask import Blueprint

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="../../templates/admin",
)

from blueprints.admin import routes  # noqa: E402,F401
