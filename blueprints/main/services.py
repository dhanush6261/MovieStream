"""
services.py (main blueprint)

Query/business logic for the public catalog pages, kept separate
from routes.py so route functions stay thin (parse request -> call
service -> render template) and the queries themselves are easy to
unit test in isolation.
"""

from flask_login import current_user
from models import Genre, Movie, WatchHistory


def get_hero_movie():
    """
    Pick the movie to show in the hero banner.

    Prefers a movie explicitly flagged is_featured; falls back to the
    highest rated movie if nothing is flagged yet (e.g. fresh seed
    data), and returns None if the catalog is empty.
    """
    movie = Movie.query.filter_by(is_featured=True).first()

    if movie is None:
        movie = Movie.query.order_by(Movie.rating.desc()).first()

    return movie


def get_trending_movies(limit=12):
    """Movies flagged as trending, most recent first."""
    return (
        Movie.query
        .filter_by(is_trending=True)
        .order_by(Movie.created_at.desc())
        .limit(limit)
        .all()
    )


def get_top_rated_movies(limit=12):
    """Highest rated movies in the catalog."""
    return (
        Movie.query
        .order_by(Movie.rating.desc())
        .limit(limit)
        .all()
    )


def get_latest_movies(limit=12):
    """Most recently added movies."""
    return (
        Movie.query
        .order_by(Movie.created_at.desc())
        .limit(limit)
        .all()
    )


def get_movies_by_genre(genre_name, limit=12):
    """All movies for a single genre row, e.g. the 'Action' shelf."""
    return (
        Movie.query
        .join(Genre)
        .filter(Genre.name == genre_name)
        .order_by(Movie.rating.desc())
        .limit(limit)
        .all()
    )


def get_genre_rows(limit_per_row=12):
    """
    Build the full set of horizontally-scrolling genre rows for the
    home page, skipping any genre that currently has zero movies so
    the page never renders an empty shelf.
    """
    rows = []

    for genre in Genre.query.order_by(Genre.name).all():
        movies = get_movies_by_genre(
            genre.name,
            limit=limit_per_row
        )

        if movies:
            rows.append({
                "genre": genre,
                "movies": movies,
            })

    return rows


def search_movies(args, limit=48):
    """
    Server-rendered search results for the /search page. Reuses the
    same query builder as the JSON API so results are always
    consistent between the live dropdown and the full results page.
    """
    from blueprints.api.services import build_movie_query

    return build_movie_query(args).limit(limit).all()


def get_continue_watching_movies(limit=12):
    """
    Return the user's watch history for Continue Watching.

    Includes both unfinished and completed movies so that a
    completed movie remains visible at 100% watched.

    Guests get an empty list because Continue Watching is
    account-specific.
    """
    if not current_user.is_authenticated:
        return []

    history_items = (
        WatchHistory.query
        .join(Movie, WatchHistory.movie_id == Movie.id)
        .filter(
            WatchHistory.user_id == current_user.id,
            WatchHistory.progress_seconds >= 0,
        )
        .order_by(WatchHistory.updated_at.desc())
        .limit(limit)
        .all()
    )

    continue_watching = []

    for history in history_items:
        progress = max(
            0,
            history.progress_seconds or 0
        )

        duration = max(
            0,
            history.duration_seconds or 0
        )

        if history.completed:
            progress_percent = 100
        elif duration > 0:
            progress_percent = min(
                99,
                (progress / duration) * 100
            )
        else:
            progress_percent = 0

        continue_watching.append({
            "movie": history.movie,
            "progress_seconds": progress,
            "duration_seconds": duration,
            "progress_percent": progress_percent,
            "completed": history.completed,
        })

    return continue_watching


def get_homepage_data():
    """
    Assemble every section the home page template needs,
    in one call.
    """
    return {
        "hero_movie": get_hero_movie(),
        "trending": get_trending_movies(),
        "top_rated": get_top_rated_movies(),
        "latest": get_latest_movies(),
        "continue_watching": get_continue_watching_movies(),
        "genre_rows": get_genre_rows(),
    }