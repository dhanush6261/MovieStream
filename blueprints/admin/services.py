"""
services.py (admin blueprint)

Dashboard stats, storage usage calculation, and category/user
management logic, kept separate from routes.py per the coding
standards.
"""

import os

from flask import current_app

from database import db
from models import Favorite, Genre, Language, Movie, User


class AdminActionError(Exception):
    """Raised when an admin action can't be completed (e.g. genre still in use)."""


def get_dashboard_stats():
    """Everything the admin dashboard needs, gathered in one call."""
    total_movies = Movie.query.count()
    total_users = User.query.count()
    total_genres = Genre.query.count()
    total_languages = Language.query.count()
    total_favorites = Favorite.query.count()

    recent_movies = Movie.query.order_by(Movie.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    most_favorited = (
        db.session.query(Movie, db.func.count(Favorite.id).label("favorite_count"))
        .join(Favorite, Favorite.movie_id == Movie.id)
        .group_by(Movie.id)
        .order_by(db.desc("favorite_count"))
        .limit(5)
        .all()
    )

    return {
        "total_movies": total_movies,
        "total_users": total_users,
        "total_genres": total_genres,
        "total_languages": total_languages,
        "total_favorites": total_favorites,
        "recent_movies": recent_movies,
        "recent_users": recent_users,
        "most_favorited": most_favorited,
        "storage": get_storage_usage(),
    }


def get_storage_usage():
    """
    Total disk space used by uploaded movies/trailers/posters, in
    bytes, plus a human-readable string. Walks the actual folders
    rather than trusting the database, so it reflects reality even if
    a file was manually dropped in or a DB row was deleted without
    cleaning up its file.
    """
    folders = [current_app.config["MOVIE_FOLDER"], current_app.config["POSTER_FOLDER"]]
    total_bytes = 0
    file_count = 0

    for folder in folders:
        if not os.path.isdir(folder):
            continue
        for filename in os.listdir(folder):
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                total_bytes += os.path.getsize(path)
                file_count += 1

    return {
        "total_bytes": total_bytes,
        "display": format_bytes(total_bytes),
        "file_count": file_count,
    }


def format_bytes(num_bytes):
    """Human-readable size, e.g. 1234567 -> '1.2 MB'."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def create_genre(name):
    name = name.strip()
    if not name:
        raise AdminActionError("Genre name can't be empty.")
    if Genre.query.filter(Genre.name.ilike(name)).first() is not None:
        raise AdminActionError(f"A genre named '{name}' already exists.")
    genre = Genre(name=name)
    db.session.add(genre)
    db.session.commit()
    return genre


def delete_genre(genre_id):
    genre = Genre.query.get(genre_id)
    if genre is None:
        raise AdminActionError("That genre no longer exists.")
    movie_count = Movie.query.filter_by(genre_id=genre_id).count()
    if movie_count > 0:
        raise AdminActionError(
            f"Can't delete '{genre.name}' -- {movie_count} movie(s) still use it. "
            f"Reassign or delete those movies first."
        )
    db.session.delete(genre)
    db.session.commit()


def toggle_user_admin(user_id, acting_user):
    user = User.query.get(user_id)
    if user is None:
        raise AdminActionError("That user no longer exists.")
    if user.id == acting_user.id:
        raise AdminActionError("You can't remove your own admin access.")
    user.is_admin = not user.is_admin
    db.session.commit()
    return user


def toggle_user_active(user_id, acting_user):
    user = User.query.get(user_id)
    if user is None:
        raise AdminActionError("That user no longer exists.")
    if user.id == acting_user.id:
        raise AdminActionError("You can't deactivate your own account.")
    user.is_active = not user.is_active
    db.session.commit()
    return user
