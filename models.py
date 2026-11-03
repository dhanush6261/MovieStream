"""
models.py

SQLAlchemy models for MovieStream.

Milestone 1: the movie catalog (Movie, Genre, Language).
Milestone 2 (User System): User accounts and server-side Favorites.
Watch History, Ratings, Comments and Downloads are still intentionally
left out -- they'll arrive with the Admin Panel / Reviews milestones
so each table ships together with the routes that use it.
"""

from datetime import datetime

from flask import url_for
from flask_login import UserMixin

from database import db


class Genre(db.Model):
    """A movie genre, e.g. Action, Drama, Sci-Fi."""

    __tablename__ = "genres"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)

    movies = db.relationship("Movie", back_populates="genre", lazy="select")

    def __repr__(self):
        return f"<Genre {self.name}>"


class Language(db.Model):
    """The spoken language of a movie, e.g. English, Hindi, Telugu."""

    __tablename__ = "languages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)

    movies = db.relationship("Movie", back_populates="language", lazy="select")

    def __repr__(self):
        return f"<Language {self.name}>"


class Movie(db.Model):
    """A single movie in the catalog."""

    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    release_year = db.Column(db.Integer, nullable=False, index=True)
    runtime_minutes = db.Column(db.Integer, nullable=False, default=0)
    rating = db.Column(db.Float, nullable=False, default=0.0, index=True)

    # Relative path under static/posters/, e.g. "neon-horizon.jpg".
    # NULL means "no poster uploaded yet" -- the template falls back
    # to a generated placeholder in that case.
    poster_path = db.Column(db.String(255), nullable=True)

    # Relative path under static/movies/ for the actual video file.
    video_path = db.Column(db.String(255), nullable=True)

    # Relative path under static/movies/ for an optional short trailer
    # clip. Nullable: not every upload includes a separate trailer.
    trailer_path = db.Column(db.String(255), nullable=True)

    # SHA-256 of the uploaded video file's bytes. Used to reject a
    # re-upload of a file that's already in the library instead of
    # silently creating a duplicate row.
    file_hash = db.Column(db.String(64), nullable=True, unique=True, index=True)

    is_trending = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    genre_id = db.Column(db.Integer, db.ForeignKey("genres.id"), nullable=False, index=True)
    language_id = db.Column(db.Integer, db.ForeignKey("languages.id"), nullable=False, index=True)

    genre = db.relationship("Genre", back_populates="movies")
    language = db.relationship("Language", back_populates="movies")

    ratings = db.relationship(
    "Rating",
    back_populates="movie",
    cascade="all, delete-orphan",
    lazy="select",
)

    watch_history = db.relationship(
        "WatchHistory",
        back_populates="movie",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def poster_url(self):
        """
        Return the URL for this movie's poster, or None if it has no
        poster yet so the template can render the placeholder card.
        Posters stay in static/ -- a thumbnail image isn't sensitive,
        unlike the actual video (see video_url/trailer_url below).
        """
        if self.poster_path:
            return f"/static/posters/{self.poster_path}"
        return None

    def video_url(self):
        """
        Return the playable URL for the main video file, or None.

        Points at the login-gated /watch/<id>/video route rather than
        a static file path -- the file itself lives outside static/
        precisely so it can't be reached without authentication.
        """
        if self.video_path:
            return url_for("movies.stream_video", movie_id=self.id)
        return None

    def trailer_url(self):
        """Return the playable URL for the trailer, or None if there isn't one."""
        if self.trailer_path:
            return url_for("movies.stream_trailer", movie_id=self.id)
        return None

    def download_url(self):
        """Return the URL that triggers a browser download of the movie, or None."""
        if self.video_path:
            return url_for("movies.download_movie", movie_id=self.id)
        return None

    def to_dict(self):
        """JSON-serializable representation used by the REST API."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "release_year": self.release_year,
            "runtime_minutes": self.runtime_minutes,
            "runtime_display": self.runtime_display(),
            "rating": self.rating,
            "poster_url": self.poster_url(),
            "video_url": self.video_url(),
            "download_url": self.download_url(),
            "trailer_url": self.trailer_url(),
            "genre": self.genre.name if self.genre else None,
            "language": self.language.name if self.language else None,
            "is_trending": self.is_trending,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat(),
        }

    def runtime_display(self):
        """Human readable runtime, e.g. '2h 8m' instead of raw minutes."""
        hours, minutes = divmod(self.runtime_minutes, 60)
        if hours and minutes:
            return f"{hours}h {minutes}m"
        if hours:
            return f"{hours}h"
        return f"{minutes}m"

    def __repr__(self):
        return f"<Movie {self.title} ({self.release_year})>"


class User(UserMixin, db.Model):
    """
    A registered account.

    Inherits UserMixin so it satisfies Flask-Login's expected
    interface (is_authenticated, is_active, get_id(), ...) without
    reimplementing those by hand.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    bio = db.Column(db.String(300), nullable=True, default="")

    # Relative path under static/avatars/. NULL falls back to the
    # generated placeholder avatar, same pattern as Movie.poster_path.
    avatar_path = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Admin Panel milestone: role and account-status flags.
    # is_active overrides UserMixin's default (which just always
    # returns True) with a real column, so an admin can disable an
    # account and have it actually block login.
    is_admin = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    favorites = db.relationship(
        "Favorite", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    ratings = db.relationship(
        "Rating",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )    

    watch_history = db.relationship(
        "WatchHistory",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def set_password(self, raw_password):
        """Hash and store a new password. Callers never touch bcrypt directly."""
        from app import bcrypt  # Local import avoids a circular import with app.py.

        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password):
        """Verify a plaintext password against the stored hash."""
        from app import bcrypt

        return bcrypt.check_password_hash(self.password_hash, raw_password)

    def avatar_url(self):
        """Return the profile photo URL, or None so templates fall back to the placeholder."""
        if self.avatar_path:
            return f"/static/avatars/{self.avatar_path}"
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "bio": self.bio,
            "avatar_url": self.avatar_url(),
            "created_at": self.created_at.isoformat(),
            "is_admin": self.is_admin,
            "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<User {self.username}>"


class Favorite(db.Model):
    """
    A user's "My List" entry, server-side and tied to their account.
    One row per (user, movie) pair -- the unique constraint is what
    makes "favoriting" idempotent (double-clicking Add can't create
    two rows).
    """

    __tablename__ = "favorites"
    __table_args__ = (
        db.UniqueConstraint("user_id", "movie_id", name="uq_favorite_user_movie"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="favorites")
    movie = db.relationship("Movie")

    def __repr__(self):
        return f"<Favorite user={self.user_id} movie={self.movie_id}>"

class Rating(db.Model):
    """
    A user's rating for a movie.

    Each user can have only one rating for a particular movie.
    If the same user rates the same movie again, the existing
    rating will be updated instead of creating another row.
    """

    __tablename__ = "ratings"

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "movie_id",
            name="uq_rating_user_movie",
        ),
        db.CheckConstraint(
            "rating >= 1 AND rating <= 10",
            name="ck_rating_1_to_10",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    movie_id = db.Column(
        db.Integer,
        db.ForeignKey("movies.id"),
        nullable=False,
        index=True,
    )

    rating = db.Column(
        db.Integer,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    user = db.relationship(
        "User",
        back_populates="ratings",
    )

    movie = db.relationship(
        "Movie",
        back_populates="ratings",
    )

    def __repr__(self):
        return (
            f"<Rating user={self.user_id} "
            f"movie={self.movie_id} rating={self.rating}>"
        )

class WatchHistory(db.Model):
    """
    Stores a user's latest watching progress for a movie.

    One row per (user, movie) pair.
    The row is updated as the user watches instead of creating
    a new row every few seconds.
    """

    __tablename__ = "watch_history"

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "movie_id",
            name="uq_watch_history_user_movie",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    movie_id = db.Column(
        db.Integer,
        db.ForeignKey("movies.id"),
        nullable=False,
        index=True,
    )

    progress_seconds = db.Column(
        db.Float,
        nullable=False,
        default=0.0,
    )

    duration_seconds = db.Column(
        db.Float,
        nullable=False,
        default=0.0,
    )

    completed = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True,
    )

    user = db.relationship(
        "User",
        back_populates="watch_history",
    )

    movie = db.relationship(
        "Movie",
        back_populates="watch_history",
    )

    def __repr__(self):
        return (
            f"<WatchHistory user={self.user_id} "
            f"movie={self.movie_id} "
            f"progress={self.progress_seconds}>"
        )