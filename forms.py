"""
forms.py

Flask-WTF form classes.

Milestone 1: MovieUploadForm powers the /upload page.
Milestone 2 (User System): RegistrationForm, LoginForm, ProfileForm,
and LogoutForm (a CSRF-only form so the navbar's logout button can
POST safely).
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Optional,
)


class MovieUploadForm(FlaskForm):
    """
    Form backing the movie upload page.

    genre and language choices are populated at request time in the
    route (they depend on what's in the database), not hard-coded
    here.
    """

    title = StringField(
        "Title", validators=[DataRequired(), Length(max=200)]
    )
    description = TextAreaField(
        "Description", validators=[DataRequired(), Length(max=4000)]
    )
    genre_id = SelectField("Genre", coerce=int, validators=[DataRequired()])
    language_id = SelectField("Language", coerce=int, validators=[DataRequired()])
    release_year = IntegerField(
        "Release Year",
        validators=[DataRequired(), NumberRange(min=1888, max=2100)],
    )

    # Optional: if left blank, the backend fills this in automatically
    # from the uploaded video's real duration (via ffprobe), when
    # available.
    runtime_minutes = IntegerField(
        "Runtime (minutes) - leave blank to auto-detect",
        validators=[Optional(), NumberRange(min=1, max=1000)],
    )

    rating = DecimalField(
        "Rating (0-10)",
        places=1,
        default=0,
        validators=[Optional(), NumberRange(min=0, max=10)],
    )

    poster = FileField(
        "Poster image (optional - auto-generated from video if omitted and ffmpeg is available)",
        validators=[
            FileAllowed(["png", "jpg", "jpeg", "webp"], "Images only (png, jpg, jpeg, webp).")
        ],
    )

    video = FileField(
        "Movie file",
        validators=[
            FileRequired("A video file is required."),
            FileAllowed(["mp4", "webm", "mov", "mkv"], "Video files only (mp4, webm, mov, mkv)."),
        ],
    )

    trailer = FileField(
        "Trailer file (optional)",
        validators=[
            FileAllowed(["mp4", "webm", "mov", "mkv"], "Video files only (mp4, webm, mov, mkv).")
        ],
    )

    is_featured = BooleanField("Feature in hero banner")
    is_trending = BooleanField("Mark as trending")


class RegistrationForm(FlaskForm):
    """New account sign-up. Username/email uniqueness is checked in the route
    (needs a DB query, which doesn't belong in a validator that runs on every
    field-level validate() call in isolation)."""

    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=50)]
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")


class ChangePasswordForm(FlaskForm):
    """Allow an authenticated user to securely change their password."""

    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Enter your current password.")],
    )

    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="Enter a new password."),
            Length(
                min=8,
                message="New password must be at least 8 characters.",
            ),
        ],
    )

    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Confirm your new password."),
            EqualTo(
                "new_password",
                message="New passwords must match.",
            ),
        ],
    )
    

class ProfileForm(FlaskForm):
    """Edit-profile form. Pre-populated from the current user in the route."""

    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=50)]
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    bio = TextAreaField("Bio", validators=[Optional(), Length(max=300)])
    avatar = FileField(
        "Profile photo (optional)",
        validators=[
            FileAllowed(["png", "jpg", "jpeg", "webp"], "Images only (png, jpg, jpeg, webp).")
        ],
    )

    remove_avatar = BooleanField(
        "Remove current profile photo",
        default=False,
    )

class LogoutForm(FlaskForm):
    """
    No visible fields -- exists purely so the navbar's logout button
    can submit a real POST with a valid CSRF token instead of being a
    bare link (a GET-triggered logout is vulnerable to being fired by
    prefetching or a stray <img> tag).
    """
    pass


class ConfirmActionForm(FlaskForm):
    """
    No visible fields -- the same CSRF-only pattern as LogoutForm,
    reused for the admin panel's delete/toggle buttons (delete movie,
    delete genre, toggle admin/active) so each is a real POST with a
    valid token instead of a bare link.
    """
    pass


class CreateGenreForm(FlaskForm):
    """Admin panel: add a new genre/category."""

    name = StringField("Genre name", validators=[DataRequired(), Length(max=50)])


class EditMovieForm(FlaskForm):
    """
    Admin panel: edit an existing movie's metadata. Unlike
    MovieUploadForm, no file is required here -- the movie already
    has a video; poster/trailer/video are only replaced if a new file
    is actually chosen.
    """

    title = StringField(
        "Title", validators=[DataRequired(), Length(max=200)]
    )
    description = TextAreaField(
        "Description", validators=[DataRequired(), Length(max=4000)]
    )
    genre_id = SelectField("Genre", coerce=int, validators=[DataRequired()])
    language_id = SelectField("Language", coerce=int, validators=[DataRequired()])
    release_year = IntegerField(
        "Release Year",
        validators=[DataRequired(), NumberRange(min=1888, max=2100)],
    )
    # InputRequired + min=0: movies registered by the library scan can
    # have runtime 0 (no ffprobe), and DataRequired treats 0 as missing,
    # which made those movies impossible to edit.
    runtime_minutes = IntegerField(
        "Runtime (minutes)",
        validators=[InputRequired(), NumberRange(min=0, max=1000)],
    )
    rating = DecimalField(
        "Rating (0-10)", places=1, validators=[Optional(), NumberRange(min=0, max=10)]
    )

    poster = FileField(
        "Replace poster (optional)",
        validators=[
            FileAllowed(["png", "jpg", "jpeg", "webp"], "Images only (png, jpg, jpeg, webp).")
        ],
    )
    video = FileField(
        "Replace movie file (optional)",
        validators=[
            FileAllowed(["mp4", "webm", "mov", "mkv"], "Video files only (mp4, webm, mov, mkv).")
        ],
    )
    trailer = FileField(
        "Replace trailer (optional)",
        validators=[
            FileAllowed(["mp4", "webm", "mov", "mkv"], "Video files only (mp4, webm, mov, mkv).")
        ],
    )

    is_featured = BooleanField("Feature in hero banner")
    is_trending = BooleanField("Mark as trending")
