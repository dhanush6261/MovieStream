"""
Defines the 'movies' blueprint: movie detail/watch pages and the
upload page. Kept separate from 'main' (which owns the home page)
so each blueprint stays focused on one area of the site.
"""

from flask import Blueprint

movies_bp = Blueprint(
    "movies",
    __name__,
    template_folder="../../templates/movies",
)

from blueprints.movies import routes  # noqa: E402,F401
