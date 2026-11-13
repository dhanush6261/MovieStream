"""
routes.py (auth blueprint)

- GET/POST /register
- GET/POST /login
- POST     /logout
- GET      /profile
- GET/POST /profile/edit
- GET/POST /profile/change-password
"""

from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from blueprints.auth import auth_bp
from blueprints.auth.services import (
    AccountDisabledError,
    PasswordChangeError,
    RegistrationError,
    authenticate_user,
    change_user_password,
    get_user_favorite_movies,
    register_user,
    update_profile,
)
from forms import ChangePasswordForm, LoginForm, ProfileForm, RegistrationForm


def is_safe_next_url(url):
    """
    Only allow redirects to a path on this site. "//evil.com" and
    "/\\evil.com" both start with "/" but browsers treat them as
    links to another host, so they're rejected explicitly.
    """
    if not url or not url.startswith("/") or url.startswith("//") or "\\" in url:
        return False
    parsed = urlparse(url)
    return not parsed.scheme and not parsed.netloc


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = register_user(form.username.data, form.email.data, form.password.data)
        except RegistrationError as exc:
            flash(str(exc), "error")
            return render_template("auth/register.html", form=form)

        login_user(user)
        flash(f"Welcome to MovieStream, {user.username}!", "success")
        return redirect(url_for("main.home", sync_favorites=1))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = authenticate_user(form.email.data, form.password.data)
        except AccountDisabledError:
            flash("This account has been disabled. Contact an administrator.", "error")
            return render_template("auth/login.html", form=form)

        if user is None:
            flash("Incorrect email or password.", "error")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        flash(f"Welcome back, {user.username}!", "success")

        next_url = request.args.get("next")
        if is_safe_next_url(next_url):
            return redirect(next_url)
        return redirect(url_for("main.home", sync_favorites=1))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/profile")
@login_required
def profile():
    favorites = get_user_favorite_movies(current_user)
    return render_template("auth/profile.html", favorites=favorites)


@auth_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        try:
            update_profile(current_user, form)
        except RegistrationError as exc:
            flash(str(exc), "error")
            return render_template("auth/edit_profile.html", form=form)

        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/edit_profile.html", form=form)


@auth_bp.route("/profile/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        try:
            change_user_password(
                current_user,
                form.current_password.data,
                form.new_password.data,
            )
        except PasswordChangeError as exc:
            flash(str(exc), "error")
            return render_template(
                "auth/change_password.html",
                form=form,
            )

        flash("Your password has been changed successfully.", "success")
        return redirect(url_for("auth.profile"))

    return render_template("auth/change_password.html", form=form)