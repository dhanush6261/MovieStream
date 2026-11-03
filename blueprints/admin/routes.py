"""
routes.py (admin blueprint)

Every route here is protected by @admin_required.

- GET      /admin                        Dashboard
- GET      /admin/movies                 List all movies
- GET/POST /admin/movies/<id>/edit        Edit a movie
- POST     /admin/movies/<id>/delete      Delete a movie
- GET/POST /admin/categories              List genres + create one
- POST     /admin/categories/<id>/delete  Delete a genre (blocked if in use)
- GET      /admin/users                   List users
- POST     /admin/users/<id>/toggle-admin
- POST     /admin/users/<id>/toggle-active
"""

from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from blueprints.admin import admin_bp
from blueprints.admin.services import (
    AdminActionError,
    create_genre,
    delete_genre,
    get_dashboard_stats,
    toggle_user_active,
    toggle_user_admin,
)
from blueprints.movies.services import (
    DuplicateVideoError,
    delete_movie_and_files,
    update_movie_from_edit_form,
)
from decorators import admin_required
from forms import ConfirmActionForm, CreateGenreForm, EditMovieForm
from models import Genre, Language, Movie, User


@admin_bp.route("/")
@admin_required
def dashboard():
    stats = get_dashboard_stats()
    return render_template("admin/dashboard.html", **stats)


@admin_bp.route("/movies")
@admin_required
def movies():
    all_movies = Movie.query.order_by(Movie.created_at.desc()).all()
    return render_template(
        "admin/movies.html", movies=all_movies, confirm_form=ConfirmActionForm()
    )


@admin_bp.route("/movies/<int:movie_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    form = EditMovieForm(obj=movie)
    form.genre_id.choices = [(g.id, g.name) for g in Genre.query.order_by(Genre.name).all()]
    form.language_id.choices = [
        (l.id, l.name) for l in Language.query.order_by(Language.name).all()
    ]
    if not form.is_submitted():
        # Pre-select the movie's current genre/language on first GET
        # (obj= populates matching-named scalar fields automatically,
        # but SelectField choices must already exist, which is why
        # this happens after .choices is set rather than via obj=).
        form.genre_id.data = movie.genre_id
        form.language_id.data = movie.language_id

    if form.validate_on_submit():
        try:
            update_movie_from_edit_form(movie, form)
        except DuplicateVideoError as exc:
            flash(str(exc), "error")
            return render_template("admin/edit_movie.html", form=form, movie=movie)

        flash(f"'{movie.title}' updated.", "success")
        return redirect(url_for("admin.movies"))

    return render_template("admin/edit_movie.html", form=form, movie=movie)


@admin_bp.route("/movies/<int:movie_id>/delete", methods=["POST"])
@admin_required
def delete_movie(movie_id):
    form = ConfirmActionForm()
    if not form.validate_on_submit():
        flash("Could not verify that request. Please try again.", "error")
        return redirect(url_for("admin.movies"))

    movie = Movie.query.get_or_404(movie_id)
    title = movie.title
    delete_movie_and_files(movie)
    flash(f"'{title}' deleted.", "success")
    return redirect(url_for("admin.movies"))


@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    form = CreateGenreForm()
    if form.validate_on_submit():
        try:
            create_genre(form.name.data)
            flash(f"Genre '{form.name.data.strip()}' created.", "success")
        except AdminActionError as exc:
            flash(str(exc), "error")
        return redirect(url_for("admin.categories"))

    genres = Genre.query.order_by(Genre.name).all()
    movie_counts = {g.id: Movie.query.filter_by(genre_id=g.id).count() for g in genres}
    return render_template(
        "admin/categories.html",
        genres=genres,
        movie_counts=movie_counts,
        form=form,
        confirm_form=ConfirmActionForm(),
    )


@admin_bp.route("/categories/<int:genre_id>/delete", methods=["POST"])
@admin_required
def delete_category(genre_id):
    form = ConfirmActionForm()
    if not form.validate_on_submit():
        flash("Could not verify that request. Please try again.", "error")
        return redirect(url_for("admin.categories"))

    try:
        delete_genre(genre_id)
        flash("Genre deleted.", "success")
    except AdminActionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template(
        "admin/users.html", users=all_users, confirm_form=ConfirmActionForm()
    )


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    form = ConfirmActionForm()
    if not form.validate_on_submit():
        flash("Could not verify that request. Please try again.", "error")
        return redirect(url_for("admin.users"))

    try:
        user = toggle_user_admin(user_id, current_user)
        flash(f"{user.username} is {'now' if user.is_admin else 'no longer'} an admin.", "success")
    except AdminActionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@admin_required
def toggle_active(user_id):
    form = ConfirmActionForm()
    if not form.validate_on_submit():
        flash("Could not verify that request. Please try again.", "error")
        return redirect(url_for("admin.users"))

    try:
        user = toggle_user_active(user_id, current_user)
        flash(f"{user.username} is {'active' if user.is_active else 'deactivated'}.", "success")
    except AdminActionError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.users"))
