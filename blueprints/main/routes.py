"""
routes.py (main blueprint)

Thin route handlers for the public catalog. Each view does the
minimum: pull request data, delegate to services.py for the actual
query logic, and render a template.
"""

from flask import render_template, request
from flask_login import current_user

from blueprints.auth.services import get_user_favorite_movies
from blueprints.main import main_bp
from blueprints.main.services import get_homepage_data, get_trending_movies, search_movies
from models import Genre, Language


@main_bp.route("/")
def home():
    """Netflix-style home page: hero banner + horizontally scrolling rows."""
    data = get_homepage_data()
    return render_template("main/home.html", **data)


@main_bp.route("/trending")
def trending():
    """All movies currently flagged is_trending, newest first."""
    movies = get_trending_movies(limit=48)
    return render_template("main/trending.html", movies=movies)


@main_bp.route("/search")
def search():
    """
    Full search-results page. Reads q/genre/language/year/min_rating
    from the query string so results are shareable/bookmarkable, and
    is hit both by pressing Enter in the navbar search box and by the
    filter form on this page itself.
    """
    movies = search_movies(request.args)
    genres = Genre.query.order_by(Genre.name).all()
    languages = Language.query.order_by(Language.name).all()
    return render_template(
        "main/search_results.html",
        movies=movies,
        genres=genres,
        languages=languages,
        query=request.args.get("q", ""),
        selected_genre=request.args.get("genre", ""),
        selected_language=request.args.get("language", ""),
        selected_year=request.args.get("year", ""),
        selected_min_rating=request.args.get("min_rating", ""),
    )


@main_bp.route("/my-list")
def my_list():
    """
    My List page.

    Logged-in users get their server-side Favorites, rendered directly
    -- no extra round trip needed. Guests still get the localStorage-
    backed version (my-list.js) so the feature keeps working without
    an account, exactly as it did before the User System milestone.
    """
    if current_user.is_authenticated:
        movies = get_user_favorite_movies(current_user, limit=100)
        return render_template("main/my_list.html", movies=movies, server_rendered=True)
    return render_template("main/my_list.html", movies=None, server_rendered=False)
