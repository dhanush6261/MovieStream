"""
services.py (movies blueprint)

Business logic for:
  - fetching a movie + related "similar movies" for the detail page
  - the full upload pipeline: validate -> save files -> hash-check
    for duplicates -> auto-detect duration/poster -> insert row

Kept separate from routes.py per the coding standards (business
logic lives outside route handlers).
"""

import os

from flask import current_app

from database import db
from media import (
    generate_poster_from_video,
    hash_file,
    minutes_from_seconds,
    probe_duration_seconds,
    save_upload,
)
from models import Movie


class DuplicateVideoError(Exception):
    """Raised when an uploaded video's hash matches an existing movie."""

    def __init__(self, existing_movie):
        self.existing_movie = existing_movie
        super().__init__(
            f"This video file already exists in the library as "
            f"'{existing_movie.title}'."
        )


def get_movie_or_none(movie_id):
    return Movie.query.get(movie_id)


def get_similar_movies(movie, limit=12):
    """Other movies in the same genre, excluding the movie itself."""
    return (
        Movie.query.filter(Movie.genre_id == movie.genre_id, Movie.id != movie.id)
        .order_by(Movie.rating.desc())
        .limit(limit)
        .all()
    )


def sync_library_from_disk():
    """
    Automatic movie detection: scan the movies folder for video files
    that have no matching Movie row yet (matched by content hash) and
    register them automatically.

    - Title is guessed from the filename (dashes/underscores -> spaces,
      title-cased).
    - A matching poster is auto-detected if a file with the same stem
      exists in the posters folder; otherwise one is generated from
      the video via ffmpeg when available.
    - Runtime is auto-detected via ffprobe when available.
    - Files that are already registered (by hash) are skipped, so
      running this repeatedly never creates duplicates.

    New movies are filed under a catch-all "Uncategorized" genre and
    "Unknown" language, which an admin can correct later from the
    admin panel (built in a later milestone) or the API.

    Returns the list of newly created Movie objects.
    """
    from datetime import datetime

    from models import Genre, Language

    video_folder = current_app.config["MOVIE_FOLDER"]
    poster_folder = current_app.config["POSTER_FOLDER"]
    allowed_ext = current_app.config["ALLOWED_VIDEO_EXTENSIONS"]

    if not os.path.isdir(video_folder):
        return []

    fallback_genre = Genre.query.filter_by(name="Uncategorized").first()
    if fallback_genre is None:
        fallback_genre = Genre(name="Uncategorized")
        db.session.add(fallback_genre)
        db.session.flush()

    fallback_language = Language.query.filter_by(name="Unknown").first()
    if fallback_language is None:
        fallback_language = Language(name="Unknown")
        db.session.add(fallback_language)
        db.session.flush()

    existing_hashes = {m.file_hash for m in Movie.query.filter(Movie.file_hash.isnot(None))}
    existing_video_paths = {m.video_path for m in Movie.query.filter(Movie.video_path.isnot(None))}

    created = []

    for filename in sorted(os.listdir(video_folder)):
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in allowed_ext:
            continue
        if filename in existing_video_paths:
            continue
        # Skip files that look like trailers of an already-registered movie.
        if filename.endswith("-trailer." + ext):
            continue

        abs_path = os.path.join(video_folder, filename)
        file_hash = hash_file(abs_path)
        if file_hash in existing_hashes:
            continue

        stem = os.path.splitext(filename)[0]
        guessed_title = stem.replace("-", " ").replace("_", " ").strip().title()

        # Auto-detect a same-named poster if one was dropped in alongside it.
        poster_filename = None
        for poster_ext in ("jpg", "jpeg", "png", "webp"):
            candidate = f"{stem}.{poster_ext}"
            if os.path.exists(os.path.join(poster_folder, candidate)):
                poster_filename = candidate
                break

        if poster_filename is None:
            os.makedirs(poster_folder, exist_ok=True)
            candidate_path = os.path.join(poster_folder, f"{stem}.jpg")
            if generate_poster_from_video(abs_path, candidate_path):
                poster_filename = f"{stem}.jpg"

        duration_seconds = probe_duration_seconds(abs_path)
        runtime_minutes = minutes_from_seconds(duration_seconds) or 0

        movie = Movie(
            title=guessed_title,
            description="Auto-detected from the movies folder. Edit this description via the API.",
            release_year=datetime.utcnow().year,
            runtime_minutes=runtime_minutes,
            rating=0.0,
            poster_path=poster_filename,
            video_path=filename,
            file_hash=file_hash,
            genre_id=fallback_genre.id,
            language_id=fallback_language.id,
        )
        db.session.add(movie)
        existing_hashes.add(file_hash)
        created.append(movie)

    if created:
        db.session.commit()

    return created


def create_movie_from_upload(
    *,
    title,
    description,
    genre_id,
    language_id,
    release_year,
    video_file,
    runtime_minutes=None,
    rating=0.0,
    poster_file=None,
    trailer_file=None,
    is_featured=False,
    is_trending=False,
):
    """
    Shared upload pipeline: save the video (and optional
    poster/trailer) to disk, detect duplicates by content hash,
    auto-fill runtime/poster when omitted, and persist the new Movie.

    Takes plain values rather than a WTForm object so both the HTML
    upload page (blueprints/movies/routes.py) and the JSON upload API
    (blueprints/api/routes.py) can call the exact same logic instead
    of duplicating it.

    Returns the created Movie. Raises DuplicateVideoError if the
    exact same video file has already been uploaded.
    """
    video_folder = current_app.config["MOVIE_FOLDER"]
    poster_folder = current_app.config["POSTER_FOLDER"]

    # --- Save the video first; we need it on disk to hash/probe it. ---
    video_filename, video_abs_path = save_upload(video_file, video_folder)

    file_hash = hash_file(video_abs_path)
    existing = Movie.query.filter_by(file_hash=file_hash).first()
    if existing is not None:
        # Clean up the just-saved duplicate file before bailing out.
        os.remove(video_abs_path)
        raise DuplicateVideoError(existing)

    # --- Optional trailer ---
    trailer_filename = None
    if trailer_file and getattr(trailer_file, "filename", ""):
        trailer_filename, _ = save_upload(trailer_file, video_folder)

    # --- Poster: use the uploaded one, or auto-generate from the video ---
    poster_filename = None
    if poster_file and getattr(poster_file, "filename", ""):
        poster_filename, _ = save_upload(poster_file, poster_folder)
    else:
        os.makedirs(poster_folder, exist_ok=True)
        candidate_name = os.path.splitext(video_filename)[0] + ".jpg"
        candidate_path = os.path.join(poster_folder, candidate_name)
        if generate_poster_from_video(video_abs_path, candidate_path):
            poster_filename = candidate_name
        # If ffmpeg isn't available, poster_filename stays None and
        # the movie card/hero fall back to the CSS placeholder --
        # never a fake stock image.

    # --- Runtime: use what was provided, or auto-detect via ffprobe ---
    if not runtime_minutes:
        duration_seconds = probe_duration_seconds(video_abs_path)
        runtime_minutes = minutes_from_seconds(duration_seconds) or 0

    movie = Movie(
        title=title.strip(),
        description=description.strip(),
        release_year=release_year,
        runtime_minutes=runtime_minutes,
        rating=float(rating or 0),
        poster_path=poster_filename,
        video_path=video_filename,
        trailer_path=trailer_filename,
        file_hash=file_hash,
        is_featured=bool(is_featured),
        is_trending=bool(is_trending),
        genre_id=genre_id,
        language_id=language_id,
    )
    db.session.add(movie)
    db.session.commit()
    return movie


def delete_movie_and_files(movie):
    """
    Delete a Movie row and its video/trailer/poster files on disk.
    Shared by the API's DELETE /api/movies/<id> and the admin panel's
    delete button, so the cleanup logic only lives in one place.
    """
    from flask import current_app

    movie_folder = current_app.config["MOVIE_FOLDER"]
    poster_folder = current_app.config["POSTER_FOLDER"]

    for filename, folder in (
        (movie.video_path, movie_folder),
        (movie.trailer_path, movie_folder),
        (movie.poster_path, poster_folder),
    ):
        if filename:
            path = os.path.join(folder, filename)
            if os.path.exists(path):
                os.remove(path)

    db.session.delete(movie)
    db.session.commit()


def update_movie_from_edit_form(movie, form):
    """
    Apply a validated EditMovieForm to an existing movie. Metadata
    fields are always updated; video/poster/trailer are only replaced
    if a new file was actually chosen, and the old file is deleted
    once the new one is safely saved.

    Raises DuplicateVideoError if a replacement video's hash matches
    a *different* movie already in the library.
    """
    from flask import current_app

    video_folder = current_app.config["MOVIE_FOLDER"]
    poster_folder = current_app.config["POSTER_FOLDER"]

    movie.title = form.title.data.strip()
    movie.description = form.description.data.strip()
    movie.genre_id = form.genre_id.data
    movie.language_id = form.language_id.data
    movie.release_year = form.release_year.data
    movie.runtime_minutes = form.runtime_minutes.data
    movie.rating = float(form.rating.data or 0)
    movie.is_featured = form.is_featured.data
    movie.is_trending = form.is_trending.data

    if form.video.data and getattr(form.video.data, "filename", ""):
        new_filename, new_abs_path = save_upload(form.video.data, video_folder)
        new_hash = hash_file(new_abs_path)

        existing = Movie.query.filter(
            Movie.file_hash == new_hash, Movie.id != movie.id
        ).first()
        if existing is not None:
            os.remove(new_abs_path)
            raise DuplicateVideoError(existing)

        old_video_path = movie.video_path
        movie.video_path = new_filename
        movie.file_hash = new_hash
        if old_video_path:
            old_abs = os.path.join(video_folder, old_video_path)
            if os.path.exists(old_abs):
                os.remove(old_abs)

    if form.poster.data and getattr(form.poster.data, "filename", ""):
        new_filename, _ = save_upload(form.poster.data, poster_folder)
        old_poster_path = movie.poster_path
        movie.poster_path = new_filename
        if old_poster_path:
            old_abs = os.path.join(poster_folder, old_poster_path)
            if os.path.exists(old_abs):
                os.remove(old_abs)

    if form.trailer.data and getattr(form.trailer.data, "filename", ""):
        new_filename, _ = save_upload(form.trailer.data, video_folder)
        old_trailer_path = movie.trailer_path
        movie.trailer_path = new_filename
        if old_trailer_path:
            old_abs = os.path.join(video_folder, old_trailer_path)
            if os.path.exists(old_abs):
                os.remove(old_abs)

    db.session.commit()
    return movie
