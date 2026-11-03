"""
app.py

Application factory and entry point for MovieStream.

Run locally with:
    python app.py

Or via Flask's own CLI:
    flask --app app run --debug
"""

import os

from flask import Flask, render_template
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate

from config import get_config
from database import db, init_db, migrate_movies_out_of_static, seed_admin_user, seed_db

# Created at module level (not inside create_app) so other modules can
# do `from app import bcrypt` / `from app import login_manager` without
# needing an app instance passed around. Bound to the actual Flask app
# via .init_app() inside create_app().
bcrypt = Bcrypt()
login_manager = LoginManager()


def create_app(config_object=None):
    """
    Application factory.

    Building the app inside a function (instead of at module import
    time) means tests, migrations, and multiple instances can each
    get their own configured app without side effects leaking
    between them.
    """
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    # --- Extensions -----------------------------------------------------
    db.init_app(app)
    Migrate(app, db)
    bcrypt.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        from models import User

        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        # API requests want a JSON 401 they can handle in JS, not a
        # redirect to an HTML login page.
        from flask import jsonify, redirect, request, url_for

        if request.path.startswith("/api/"):
            return jsonify({"error": "Login required."}), 401
        return redirect(url_for("auth.login", next=request.path))

    # --- Blueprints -------------------------------------------------------
    from blueprints.main import main_bp
    from blueprints.movies import movies_bp
    from blueprints.api import api_bp
    from blueprints.auth import auth_bp
    from blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(movies_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    # --- Error handlers ---------------------------------------------------
    register_error_handlers(app)

    # --- Template context ---------------------------------------------------
    register_context_processors(app)

    # --- CLI commands -------------------------------------------------------
    register_cli_commands(app)

    return app


def register_error_handlers(app):
    """Custom dark-themed error pages instead of Flask's default plain text."""

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        max_gb = app.config["MAX_CONTENT_LENGTH"] / (1024 ** 3)
        return render_template("errors/413.html", max_gb=max_gb), 413

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500


def register_cli_commands(app):
    """Custom `flask` CLI commands for local admin/dev tasks."""
    import click

    @app.cli.command("create-admin")
    @click.argument("email")
    def create_admin(email):
        """Promote an existing user (by email) to admin. Usage: flask --app app create-admin someone@example.com"""
        from models import User

        user = User.query.filter_by(email=email.lower()).first()
        if user is None:
            click.echo(f"No user found with email '{email}'.")
            return
        user.is_admin = True
        db.session.commit()
        click.echo(f"'{user.username}' ({user.email}) is now an admin.")


def register_context_processors(app):
    """Makes shared template globals available on every page without
    every single route having to pass them in explicitly."""

    @app.context_processor
    def inject_logout_form():
        from forms import LogoutForm

        # A tiny CSRF-only form so the navbar's logout button can POST
        # safely from any page, not just pages whose route happens to
        # build a LogoutForm itself.
        #
        # Guarded: if the current request is itself an oversized
        # multipart upload that already triggered a 413, constructing
        # any FlaskForm here touches request.files, which re-reads the
        # (already-too-large) body and re-raises the same error while
        # we're trying to render the error page. Falling back to None
        # lets 413.html (and any other error page) still render; the
        # navbar template skips the logout form in that case.
        try:
            return {"logout_form": LogoutForm()}
        except Exception:
            return {"logout_form": None}


# Module-level app instance so `flask --app app run` and WSGI servers
# (gunicorn app:app) can find it directly.
app = create_app()


if __name__ == "__main__":
    # Make sure the instance/ folder exists for the SQLite file.
    os.makedirs(os.path.join(os.path.dirname(__file__), "instance"), exist_ok=True)

    init_db(app)
    migrate_movies_out_of_static(app)
    seed_db(app)
    seed_admin_user(app)

    app.run(debug=app.config.get("DEBUG", True))
