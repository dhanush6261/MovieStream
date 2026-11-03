"""
routes.py (movies blueprint)

- GET  /movie/<id>              Movie detail + player page.
- GET  /upload                  Upload form (ADMIN ONLY).
- POST /upload                  Handle the upload (ADMIN ONLY).
- GET  /watch/<id>/video         Stream the movie file (login required).
- GET  /watch/<id>/trailer       Stream the trailer file (login required).
- GET  /watch/<id>/download      Download the movie file (login required).

Uploading is an admin-only capability: normal users must not see the
Upload link (hidden in the navbar) and must not be able to reach
/upload even via a direct URL (enforced server-side below via
@admin_required, not just by hiding the link). See decorators.py:
not-logged-in visitors are redirected to login, logged-in non-admins
get a real 403.

The three /watch/... routes are the ONLY way movie/trailer bytes ever
reach a browser: the files live in MOVIE_FOLDER, which is outside
static/, so Flask never serves them to an unauthenticated request.
send_from_directory(..., conditional=True) gives Range/ETag/206
support for free (seeking, resuming) without loading the whole file
into memory, and safely resolves the filename against MOVIE_FOLDER --
there's no user-controlled path here (movie_id is just an integer
looked up in the DB), so path traversal isn't reachable through this
route by construction.
"""

from flask import abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import login_required
from werkzeug.utils import secure_filename

from blueprints.movies import movies_bp
from blueprints.movies.services import (
    DuplicateVideoError,
    create_movie_from_upload,
    get_movie_or_none,
    get_similar_movies,
)
from decorators import admin_required
from forms import MovieUploadForm
from models import Genre, Language


@movies_bp.route("/movie/<int:movie_id>")
def detail(movie_id):
    """Movie detail page with the embedded player, metadata, and similar movies."""
    movie = get_movie_or_none(movie_id)
    if movie is None:
        abort(404)
    similar = get_similar_movies(movie)
    autoplay = request.args.get("autoplay") == "1"
    return render_template(
        "movies/detail.html", movie=movie, similar=similar, autoplay=autoplay
    )


@movies_bp.route("/watch/<int:movie_id>/video")
@login_required
def stream_video(movie_id):
    movie = get_movie_or_none(movie_id)
    if movie is None or not movie.video_path:
        abort(404)
    return send_from_directory(
        current_app.config["MOVIE_FOLDER"], movie.video_path, conditional=True
    )


@movies_bp.route("/watch/<int:movie_id>/trailer")
@login_required
def stream_trailer(movie_id):
    movie = get_movie_or_none(movie_id)
    if movie is None or not movie.trailer_path:
        abort(404)
    return send_from_directory(
        current_app.config["MOVIE_FOLDER"], movie.trailer_path, conditional=True
    )


@movies_bp.route("/watch/<int:movie_id>/download")
@login_required
def download_movie(movie_id):
    movie = get_movie_or_none(movie_id)
    if movie is None or not movie.video_path:
        abort(404)
    ext = movie.video_path.rsplit(".", 1)[-1] if "." in movie.video_path else "mp4"
    safe_name = secure_filename(f"{movie.title}.{ext}") or movie.video_path
    return send_from_directory(
        current_app.config["MOVIE_FOLDER"],
        movie.video_path,
        as_attachment=True,
        download_name=safe_name,
        conditional=True,
    )


@movies_bp.route("/upload", methods=["GET", "POST"])
@admin_required
def upload():
    """Movie upload page: GET renders the form, POST processes it. Admin-only."""
    form = MovieUploadForm()
    form.genre_id.choices = [(g.id, g.name) for g in Genre.query.order_by(Genre.name).all()]
    form.language_id.choices = [
        (l.id, l.name) for l in Language.query.order_by(Language.name).all()
    ]

    if form.validate_on_submit():
        try:
            movie = create_movie_from_upload(
                title=form.title.data,
                description=form.description.data,
                genre_id=form.genre_id.data,
                language_id=form.language_id.data,
                release_year=form.release_year.data,
                runtime_minutes=form.runtime_minutes.data,
                rating=float(form.rating.data or 0),
                video_file=form.video.data,
                poster_file=form.poster.data,
                trailer_file=form.trailer.data,
                is_featured=form.is_featured.data,
                is_trending=form.is_trending.data,
            )
        except DuplicateVideoError as exc:
            flash(str(exc), "error")
            return render_template("movies/upload.html", form=form), 409

        flash(f"'{movie.title}' was uploaded successfully.", "success")
        return redirect(url_for("movies.detail", movie_id=movie.id))

    return render_template("movies/upload.html", form=form)
