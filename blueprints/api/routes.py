"""
routes.py (api blueprint)

REST endpoints consumed by the frontend JS (api.js, search.js,
player.js, movie-card.js) instead of full page reloads.

Endpoints:
    GET    /api/movies              List + search + filter + sort + paginate
    GET    /api/movies/search       Lightweight search for the navbar live dropdown
    POST   /api/movies/upload       Create a movie from an uploaded video (+ optional poster/trailer) (ADMIN ONLY)
    GET    /api/movies/<id>         Single movie
    PATCH  /api/movies/<id>         Partial update (ADMIN ONLY)
    DELETE /api/movies/<id>         Delete a movie (and its files) (ADMIN ONLY)
    POST   /api/movies/scan         Automatic movie detection: register any new files in media/movies (ADMIN ONLY)
    GET    /api/genres              List of genres
    GET    /api/languages           List of languages

    GET    /api/favorites            Current user's favorited movies (login required)
    POST   /api/favorites            Add a favorite: {"movie_id": int} (login required)
    DELETE /api/favorites/<movie_id> Remove a favorite (login required)
    POST   /api/favorites/sync       Bulk-add: {"movie_ids": [int, ...]} -- used to migrate a
                                      guest's localStorage list onto the account right after login
"""

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from blueprints.api import api_bp
from blueprints.api.services import build_movie_query, paginate
from decorators import admin_required
from blueprints.movies.services import (
    DuplicateVideoError,
    create_movie_from_upload,
    delete_movie_and_files,
    sync_library_from_disk,
)
from database import db
from media import allowed_image, allowed_video
from models import Favorite, Genre, Language, Movie, Rating, WatchHistory


@api_bp.route("/movies")
def list_movies():
    query = build_movie_query(request.args)
    result = paginate(query, request.args)
    return jsonify({
        "movies": [m.to_dict() for m in result.items],
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
    })


@api_bp.route("/movies/search")
def search_movies():
    """Lightweight endpoint for the navbar's live search dropdown."""
    query = build_movie_query(request.args)
    limit = min(request.args.get("limit", 8, type=int), 20)
    movies = query.limit(limit).all()
    return jsonify({"movies": [m.to_dict() for m in movies]})


@api_bp.route("/movies/<int:movie_id>")
def get_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    return jsonify(movie.to_dict())


@api_bp.route("/movies/upload", methods=["POST"])
@admin_required
def upload_movie():
    """
    JSON/multipart upload endpoint (multipart/form-data), for
    programmatic clients. The human-facing /upload page (movies
    blueprint) posts here conceptually but actually calls the shared
    service function directly to render a friendly HTML page instead
    of JSON.
    """
    required_fields = ["title", "description", "genre_id", "language_id", "release_year"]
    missing = [f for f in required_fields if not request.form.get(f)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    video_file = request.files.get("video")
    if video_file is None or video_file.filename == "":
        return jsonify({"error": "A video file is required."}), 400
    if not allowed_video(video_file.filename):
        return jsonify({"error": "Unsupported video format."}), 400

    poster_file = request.files.get("poster")
    if poster_file and poster_file.filename and not allowed_image(poster_file.filename):
        return jsonify({"error": "Unsupported poster image format."}), 400

    trailer_file = request.files.get("trailer")
    if trailer_file and trailer_file.filename and not allowed_video(trailer_file.filename):
        return jsonify({"error": "Unsupported trailer video format."}), 400

    try:
        genre_id = int(request.form["genre_id"])
        language_id = int(request.form["language_id"])
        release_year = int(request.form["release_year"])
    except ValueError:
        return jsonify({"error": "genre_id, language_id, and release_year must be integers."}), 400

    if Genre.query.get(genre_id) is None:
        return jsonify({"error": f"Genre {genre_id} does not exist."}), 400
    if Language.query.get(language_id) is None:
        return jsonify({"error": f"Language {language_id} does not exist."}), 400

    runtime_minutes = request.form.get("runtime_minutes", type=int)
    rating = request.form.get("rating", type=float) or 0.0

    try:
        movie = create_movie_from_upload(
            title=request.form["title"],
            description=request.form["description"],
            genre_id=genre_id,
            language_id=language_id,
            release_year=release_year,
            runtime_minutes=runtime_minutes,
            rating=rating,
            video_file=video_file,
            poster_file=poster_file if poster_file and poster_file.filename else None,
            trailer_file=trailer_file if trailer_file and trailer_file.filename else None,
            is_featured=request.form.get("is_featured", "false").lower() == "true",
            is_trending=request.form.get("is_trending", "false").lower() == "true",
        )
    except DuplicateVideoError as exc:
        return jsonify({"error": str(exc), "existing_movie_id": exc.existing_movie.id}), 409

    return jsonify(movie.to_dict()), 201


@api_bp.route("/movies/<int:movie_id>", methods=["PATCH", "PUT"])
@admin_required
def update_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    data = request.get_json(silent=True) or {}

    editable_fields = {
        "title": str,
        "description": str,
        "release_year": int,
        "runtime_minutes": int,
        "rating": float,
        "genre_id": int,
        "language_id": int,
        "is_trending": bool,
        "is_featured": bool,
    }

    for field, caster in editable_fields.items():
        if field in data:
            try:
                setattr(movie, field, caster(data[field]))
            except (TypeError, ValueError):
                return jsonify({"error": f"Invalid value for '{field}'."}), 400

    if "genre_id" in data and Genre.query.get(movie.genre_id) is None:
        return jsonify({"error": "genre_id does not exist."}), 400
    if "language_id" in data and Language.query.get(movie.language_id) is None:
        return jsonify({"error": "language_id does not exist."}), 400

    db.session.commit()
    return jsonify(movie.to_dict())


@api_bp.route("/movies/<int:movie_id>", methods=["DELETE"])
@admin_required
def delete_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    delete_movie_and_files(movie)
    return jsonify({"deleted": movie_id})


@api_bp.route("/movies/scan", methods=["POST"])
@admin_required
def scan_library():
    """Automatic movie detection: register any new files dropped into media/movies."""
    created = sync_library_from_disk()
    return jsonify({
        "created_count": len(created),
        "movies": [m.to_dict() for m in created],
    })


@api_bp.route("/genres")
def list_genres():
    genres = Genre.query.order_by(Genre.name).all()
    return jsonify([{"id": g.id, "name": g.name} for g in genres])


@api_bp.route("/languages")
def list_languages():
    languages = Language.query.order_by(Language.name).all()
    return jsonify([{"id": l.id, "name": l.name} for l in languages])

@api_bp.route("/movies/<int:movie_id>/rating")
def get_movie_rating(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    ratings = Rating.query.filter_by(movie_id=movie.id)

    average = db.session.query(
        db.func.avg(Rating.rating)
    ).filter(
        Rating.movie_id == movie.id
    ).scalar()

    count = ratings.count()

    user_rating = None

    if current_user.is_authenticated:
        existing = Rating.query.filter_by(
            user_id=current_user.id,
            movie_id=movie.id
        ).first()

        if existing:
            user_rating = existing.rating

    return jsonify({
        "movie_id": movie.id,
        "average_rating": round(float(average), 1) if average is not None else 0,
        "rating_count": count,
        "user_rating": user_rating,
    })


@api_bp.route("/movies/<int:movie_id>/rating", methods=["POST"])
@login_required
def submit_movie_rating(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    data = request.get_json(silent=True) or {}
    rating_value = data.get("rating")

    try:
        rating_value = int(rating_value)
    except (TypeError, ValueError):
        return jsonify({
            "error": "Rating must be an integer from 1 to 10."
        }), 400

    if rating_value < 1 or rating_value > 10:
        return jsonify({
            "error": "Rating must be between 1 and 10."
        }), 400

    existing = Rating.query.filter_by(
        user_id=current_user.id,
        movie_id=movie.id
    ).first()

    if existing:
        existing.rating = rating_value
    else:
        existing = Rating(
            user_id=current_user.id,
            movie_id=movie.id,
            rating=rating_value,
        )
        db.session.add(existing)

    db.session.commit()

    average = db.session.query(
        db.func.avg(Rating.rating)
    ).filter(
        Rating.movie_id == movie.id
    ).scalar()

    count = Rating.query.filter_by(movie_id=movie.id).count()

    return jsonify({
        "message": "Rating saved successfully.",
        "movie_id": movie.id,
        "user_rating": rating_value,
        "average_rating": round(float(average), 1) if average is not None else 0,
        "rating_count": count,
    })


@api_bp.route("/movies/<int:movie_id>/rating", methods=["DELETE"])
@login_required
def delete_movie_rating(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    existing = Rating.query.filter_by(
        user_id=current_user.id,
        movie_id=movie.id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()

    average = db.session.query(
        db.func.avg(Rating.rating)
    ).filter(
        Rating.movie_id == movie.id
    ).scalar()

    count = Rating.query.filter_by(movie_id=movie.id).count()

    return jsonify({
        "message": "Rating removed successfully.",
        "movie_id": movie.id,
        "user_rating": None,
        "average_rating": round(float(average), 1) if average is not None else 0,
        "rating_count": count,
    })

@api_bp.route("/movies/<int:movie_id>/watch-history")
@login_required
def get_watch_history(movie_id):
    """Return the current user's saved watching progress for a movie."""
    movie = Movie.query.get_or_404(movie_id)

    history = WatchHistory.query.filter_by(
        user_id=current_user.id,
        movie_id=movie.id,
    ).first()

    if history is None:
        return jsonify({
            "movie_id": movie.id,
            "progress_seconds": 0,
            "duration_seconds": 0,
            "completed": False,
            "updated_at": None,
        })

    return jsonify({
        "movie_id": movie.id,
        "progress_seconds": history.progress_seconds,
        "duration_seconds": history.duration_seconds,
        "completed": history.completed,
        "updated_at": history.updated_at.isoformat(),
    })


@api_bp.route("/movies/<int:movie_id>/watch-history", methods=["POST"])
@login_required
def save_watch_history(movie_id):
    """Create or update the current user's watching progress."""
    movie = Movie.query.get_or_404(movie_id)

    data = request.get_json(silent=True) or {}

    progress = data.get("progress_seconds")
    duration = data.get("duration_seconds")

    try:
        progress = float(progress)
        duration = float(duration)
    except (TypeError, ValueError):
        return jsonify({
            "error": "progress_seconds and duration_seconds must be numbers."
        }), 400

    if progress < 0:
        return jsonify({
            "error": "progress_seconds cannot be negative."
        }), 400

    if duration < 0:
        return jsonify({
            "error": "duration_seconds cannot be negative."
        }), 400

    if duration > 0 and progress > duration:
        progress = duration

    completed = bool(data.get("completed", False))

    # Automatically mark the movie completed when the user reaches
    # at least 95% of the available duration.
    if duration > 0 and progress >= duration * 0.95:
        completed = True

    history = WatchHistory.query.filter_by(
        user_id=current_user.id,
        movie_id=movie.id,
    ).first()

    if history is None:
        history = WatchHistory(
            user_id=current_user.id,
            movie_id=movie.id,
            progress_seconds=progress,
            duration_seconds=duration,
            completed=completed,
        )
        db.session.add(history)
    else:
        history.progress_seconds = progress
        history.duration_seconds = duration
        history.completed = completed

    db.session.commit()

    return jsonify({
        "message": "Watch progress saved successfully.",
        "movie_id": movie.id,
        "progress_seconds": history.progress_seconds,
        "duration_seconds": history.duration_seconds,
        "completed": history.completed,
        "updated_at": history.updated_at.isoformat(),
    })


@api_bp.route("/watch-history")
@login_required
def list_watch_history():
    """Return the current user's recent watch history."""
    history_items = (
        WatchHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(WatchHistory.updated_at.desc())
        .all()
    )

    return jsonify({
        "history": [
            {
                "movie_id": item.movie.id,
                "title": item.movie.title,
                "poster_url": item.movie.poster_url(),
                "progress_seconds": item.progress_seconds,
                "duration_seconds": item.duration_seconds,
                "completed": item.completed,
                "updated_at": item.updated_at.isoformat(),
            }
            for item in history_items
        ]
    })


@api_bp.route("/movies/<int:movie_id>/watch-history", methods=["DELETE"])
@login_required
def delete_watch_history(movie_id):
    """Remove the current user's watch history for a movie."""
    movie = Movie.query.get_or_404(movie_id)

    history = WatchHistory.query.filter_by(
        user_id=current_user.id,
        movie_id=movie.id,
    ).first()

    if history is not None:
        db.session.delete(history)
        db.session.commit()

    return jsonify({
        "message": "Watch history removed successfully.",
        "movie_id": movie.id,
    })

@api_bp.route("/favorites")
@login_required
def list_favorites():
    movies = (
        Movie.query.join(Favorite, Favorite.movie_id == Movie.id)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    return jsonify({"movies": [m.to_dict() for m in movies]})


@api_bp.route("/favorites", methods=["POST"])
@login_required
def add_favorite():
    data = request.get_json(silent=True) or {}
    movie_id = data.get("movie_id")
    if not movie_id:
        return jsonify({"error": "movie_id is required."}), 400
    if Movie.query.get(movie_id) is None:
        return jsonify({"error": "Movie not found."}), 404

    existing = Favorite.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if existing is None:
        db.session.add(Favorite(user_id=current_user.id, movie_id=movie_id))
        db.session.commit()

    return jsonify({"favorited": True, "movie_id": movie_id}), 201


@api_bp.route("/favorites/<int:movie_id>", methods=["DELETE"])
@login_required
def remove_favorite(movie_id):
    favorite = Favorite.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if favorite is not None:
        db.session.delete(favorite)
        db.session.commit()
    return jsonify({"favorited": False, "movie_id": movie_id})


@api_bp.route("/favorites/sync", methods=["POST"])
@login_required
def sync_favorites():
    """
    Bulk-add favorites. Used once, right after login, to migrate a
    guest's localStorage "My List" onto their new account instead of
    silently losing it.
    """
    data = request.get_json(silent=True) or {}
    movie_ids = data.get("movie_ids", [])
    if not isinstance(movie_ids, list):
        return jsonify({"error": "movie_ids must be a list."}), 400

    existing_ids = {
        f.movie_id
        for f in Favorite.query.filter_by(user_id=current_user.id).all()
    }
    valid_movie_ids = {
        m.id for m in Movie.query.filter(Movie.id.in_(movie_ids)).all()
    }

    added = 0
    for movie_id in valid_movie_ids - existing_ids:
        db.session.add(Favorite(user_id=current_user.id, movie_id=movie_id))
        added += 1

    if added:
        db.session.commit()

    return jsonify({"added_count": added})
