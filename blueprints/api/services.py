"""
services.py (api blueprint)

Builds the SQLAlchemy query for GET /api/movies from request query
parameters: free-text search, genre/language/year/rating filters,
sorting, an explicit id list (used by the "My List" page), and
pagination. Kept separate from routes.py so the query logic can be
tested independently of the HTTP layer.
"""

from sqlalchemy.orm import contains_eager

from models import Genre, Language, Movie

SORT_OPTIONS = {
    "rating": Movie.rating.desc(),
    "latest": Movie.created_at.desc(),
    "oldest": Movie.created_at.asc(),
    "title": Movie.title.asc(),
    "year": Movie.release_year.desc(),
}


def build_movie_query(args):
    """
    args: a Flask request.args-like mapping (MultiDict).
    Supported params: q, genre, language, year, min_rating, ids, sort.
    """
    # contains_eager reuses these joins to fill movie.genre/movie.language,
    # so to_dict() doesn't fire two extra queries per movie.
    query = (
        Movie.query.join(Movie.genre)
        .join(Movie.language)
        .options(contains_eager(Movie.genre), contains_eager(Movie.language))
    )

    q = args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        query = query.filter(
            Movie.title.ilike(like) | Movie.description.ilike(like)
        )

    genre = args.get("genre", "").strip()
    if genre:
        query = query.filter(Genre.name.ilike(genre))

    language = args.get("language", "").strip()
    if language:
        query = query.filter(Language.name.ilike(language))

    year = args.get("year", type=int)
    if year:
        query = query.filter(Movie.release_year == year)

    min_rating = args.get("min_rating", type=float)
    if min_rating is not None:
        query = query.filter(Movie.rating >= min_rating)

    ids_param = args.get("ids", "").strip()
    if ids_param:
        try:
            id_list = [int(x) for x in ids_param.split(",") if x.strip()]
        except ValueError:
            id_list = []
        query = query.filter(Movie.id.in_(id_list))

    sort_key = args.get("sort", "latest")
    query = query.order_by(SORT_OPTIONS.get(sort_key, Movie.created_at.desc()))

    return query


def paginate(query, args, default_per_page=24, max_per_page=100):
    page = args.get("page", 1, type=int)
    per_page = min(args.get("per_page", default_per_page, type=int), max_per_page)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination
