"""
decorators.py

Shared route decorators. Currently just admin_required, but kept as
its own module (rather than tucked inside one blueprint) since more
than one blueprint (admin pages, movie upload, and admin-only API
endpoints) needs the exact same check.
"""

from functools import wraps

from flask import abort, jsonify, redirect, request, url_for
from flask_login import current_user


def admin_required(view_func):
    """
    Require the current user to be logged in AND flagged is_admin.

    Enforced server-side on the route itself -- this is what actually
    blocks access, independent of whether a link is hidden in the UI.
    A user who navigates straight to a protected URL, or POSTs to it
    directly (curl, a saved bookmark, browser devtools), hits this
    exact same check.

    For HTML pages: not-logged-in visitors are redirected to login;
    a logged-in non-admin gets a real 403 page.

    For JSON API routes (path starts with /api/): not-logged-in
    requests get a 401 JSON body instead of an HTML redirect, and a
    logged-in non-admin gets a 403 JSON body -- consistent with how
    login_manager.unauthorized_handler in app.py already treats /api/
    differently from regular pages.
    """

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        is_api_request = request.path.startswith("/api/")

        if not current_user.is_authenticated:
            if is_api_request:
                return jsonify({"error": "Login required."}), 401
            return redirect(url_for("auth.login", next=request.path))

        if not current_user.is_admin:
            if is_api_request:
                return jsonify({"error": "Admin access required."}), 403
            abort(403)

        return view_func(*args, **kwargs)

    return wrapped
