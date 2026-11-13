"""
services.py (auth blueprint)

Registration, authentication, and profile-update logic, kept separate
from routes.py per the coding standards.
"""

import os

from flask import current_app

from database import db
from media import save_upload
from models import Favorite, Movie, User


class RegistrationError(Exception):
    """Raised when a username or email is already taken."""


class AccountDisabledError(Exception):
    """Raised when correct credentials are given for a deactivated account."""


class PasswordChangeError(Exception):
    """Raised when a password change request cannot be completed."""


def register_user(username, email, password):
    if User.query.filter_by(username=username).first() is not None:
        raise RegistrationError("That username is already taken.")
    if User.query.filter_by(email=email.lower()).first() is not None:
        raise RegistrationError("An account with that email already exists.")

    user = User(username=username, email=email.lower())
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate_user(email, password):
    """
    Return the User if the email/password match. Returns None for a
    wrong email/password (so the login route shows a generic error and
    doesn't leak which part was wrong). Raises AccountDisabledError
    for otherwise-correct credentials on a deactivated account, so the
    user gets an accurate message instead of "incorrect password".
    """
    user = User.query.filter_by(email=email.lower()).first()
    if user is None or not user.check_password(password):
        return None
    if not user.is_active:
        raise AccountDisabledError()
    return user


def change_user_password(user, current_password, new_password):
    """
    Change the authenticated user's password after verifying the
    current password.
    """
    if not user.check_password(current_password):
        raise PasswordChangeError("Current password is incorrect.")

    if current_password == new_password:
        raise PasswordChangeError(
            "New password must be different from your current password."
        )

    user.set_password(new_password)
    db.session.commit()
    return user


def update_profile(user, form):
    """
    Apply a validated ProfileForm to `user`.

    Handles:
    - username/email uniqueness
    - bio update
    - avatar upload
    - avatar removal
    - cleanup of the previous avatar file

    If a new avatar is uploaded, it takes priority over
    the remove-avatar checkbox.
    """
    new_username = form.username.data
    new_email = form.email.data.lower()

    existing_username = User.query.filter_by(username=new_username).first()
    if existing_username is not None and existing_username.id != user.id:
        raise RegistrationError("That username is already taken.")

    existing_email = User.query.filter_by(email=new_email).first()
    if existing_email is not None and existing_email.id != user.id:
        raise RegistrationError("An account with that email already exists.")

    user.username = new_username
    user.email = new_email
    user.bio = form.bio.data

    avatar_folder = current_app.config["AVATAR_FOLDER"]
    old_path = user.avatar_path
    new_abs = None

    # 1. New avatar uploaded (takes priority over the remove checkbox).
    if form.avatar.data and getattr(form.avatar.data, "filename", ""):
        user.avatar_path, new_abs = save_upload(form.avatar.data, avatar_folder)
    # 2. User requested avatar removal.
    elif form.remove_avatar.data and old_path:
        user.avatar_path = None

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        if new_abs and os.path.exists(new_abs):
            os.remove(new_abs)
        raise

    # Only delete the previous file once the DB no longer points at it.
    if old_path and user.avatar_path != old_path:
        old_abs = os.path.join(avatar_folder, old_path)
        if os.path.exists(old_abs):
            os.remove(old_abs)
    return user

def get_user_favorite_movies(user, limit=24):
    """Movies the user has favorited, most recently added first."""
    return (
        Movie.query.join(Favorite, Favorite.movie_id == Movie.id)
        .filter(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
        .all()
    )
