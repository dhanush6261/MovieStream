"""
database.py

Owns the single SQLAlchemy() instance used across the whole app, plus
helper functions for creating tables and loading seed data.

Keeping this in its own module (instead of app.py) avoids circular
imports: models.py imports `db` from here, blueprints import models,
and app.py imports both -- nothing imports app.py back.
"""

from flask_sqlalchemy import SQLAlchemy

# Single shared SQLAlchemy instance. Bound to the Flask app later via
# db.init_app(app) inside the application factory in app.py.
db = SQLAlchemy()


def init_db(app):
    """
    Create all tables that don't already exist yet.

    Safe to call every time the app starts: SQLAlchemy's create_all()
    is a no-op for tables that are already present, so existing data
    is never touched or dropped.
    """
    with app.app_context():
        db.create_all()


def seed_db(app):
    """
    Populate the database with sample data for local development.

    Only inserts data if the Movie table is empty, so re-running this
    (e.g. on every app start) never creates duplicates.

    The seeded movies reference real, playable files bundled under
    static/movies/ and static/posters/ (short original demo clips
    generated for this project -- not real film content, since actual
    copyrighted movies obviously can't be shipped in the repo). This
    means Play/Trailer/My List all work against genuine files out of
    the box; upload your own videos via /upload to add real content.
    """
    import os

    from flask import current_app

    from media import hash_file
    from models import Genre, Language, Movie

    with app.app_context():
        if Movie.query.first() is not None:
            return  # Already seeded, nothing to do.

        genre_names = [
            "Action", "Comedy", "Sci-Fi", "Thriller", "Romance",
            "Horror", "Drama", "Animation", "Family", "Documentary",
            "Crime", "Fantasy", "Adventure",
        ]
        genres = {name: Genre(name=name) for name in genre_names}
        db.session.add_all(genres.values())

        language_names = ["English", "Hindi", "Telugu", "Tamil", "Korean"]
        languages = {name: Language(name=name) for name in language_names}
        db.session.add_all(languages.values())

        db.session.flush()  # Assign IDs without committing yet.

        sample_movies = [
            {
                "title": "Neon Horizon",
                "description": "A rogue pilot races against time to stop an "
                                "orbital weapon from igniting a new war.",
                "release_year": 2025,
                "runtime_minutes": 128,
                "rating": 8.4,
                "slug": "neon-horizon",
                "genre": "Sci-Fi",
                "language": "English",
                "is_featured": True,
                "is_trending": True,
            },
            {
                "title": "Midnight Ledger",
                "description": "A forensic accountant uncovers a conspiracy "
                                "that reaches the top of her own firm.",
                "release_year": 2024,
                "runtime_minutes": 111,
                "rating": 7.6,
                "slug": "midnight-ledger",
                "genre": "Thriller",
                "language": "English",
                "is_featured": False,
                "is_trending": True,
            },
            {
                "title": "Second Sunrise",
                "description": "Two estranged sisters reunite for one last "
                                "summer at their grandmother's coastal home.",
                "release_year": 2023,
                "runtime_minutes": 104,
                "rating": 7.9,
                "slug": "second-sunrise",
                "genre": "Drama",
                "language": "Hindi",
                "is_featured": False,
                "is_trending": False,
            },
            {
                "title": "The Static Hour",
                "description": "A late-night radio host starts receiving "
                                "calls from a town that no longer exists.",
                "release_year": 2025,
                "runtime_minutes": 96,
                "rating": 8.1,
                "slug": "the-static-hour",
                "genre": "Horror",
                "language": "English",
                "is_featured": False,
                "is_trending": True,
            },
            {
                "title": "Paper Kingdoms",
                "description": "An animated tale of two rival kite-making "
                                "villages who must unite to survive a storm.",
                "release_year": 2022,
                "runtime_minutes": 92,
                "rating": 8.7,
                "slug": "paper-kingdoms",
                "genre": "Animation",
                "language": "Tamil",
                "is_featured": False,
                "is_trending": False,
            },
            {
                "title": "Last Call at Comet Diner",
                "description": "On the final night before it closes forever, "
                                "a roadside diner brings six strangers together.",
                "release_year": 2024,
                "runtime_minutes": 101,
                "rating": 7.3,
                "slug": "last-call-at-comet-diner",
                "genre": "Comedy",
                "language": "English",
                "is_featured": False,
                "is_trending": False,
            },
        ]

        movie_folder = current_app.config["MOVIE_FOLDER"]

        for data in sample_movies:
            video_filename = f"{data['slug']}.mp4"
            trailer_filename = f"{data['slug']}-trailer.mp4"
            poster_filename = f"{data['slug']}.jpg"

            video_abs_path = os.path.join(movie_folder, video_filename)
            file_hash = hash_file(video_abs_path) if os.path.exists(video_abs_path) else None

            movie = Movie(
                title=data["title"],
                description=data["description"],
                release_year=data["release_year"],
                runtime_minutes=data["runtime_minutes"],
                rating=data["rating"],
                poster_path=poster_filename,
                video_path=video_filename,
                trailer_path=trailer_filename,
                file_hash=file_hash,
                is_featured=data["is_featured"],
                is_trending=data["is_trending"],
                genre=genres[data["genre"]],
                language=languages[data["language"]],
            )
            db.session.add(movie)

        db.session.commit()


def seed_admin_user(app):
    """
    Create a default admin account for local development, so the
    Admin Panel is usable immediately without a manual CLI step.

    Only runs if there are zero users in the database yet, so it
    never touches an existing install and never creates a duplicate.
    Kept separate from seed_db() (which seeds movies) since the two
    are independent concerns -- an install with movies but no users
    yet should still get an admin account.
    """
    import os

    from models import User

    # The well-known admin123 password is only acceptable on a local
    # debug run. Anywhere else, ADMIN_PASSWORD must be set explicitly
    # (or promote a registered user with `flask create-admin`).
    password = os.environ.get("ADMIN_PASSWORD") or ("admin123" if app.config.get("DEBUG") else None)
    if not password:
        print("[seed_admin_user] Skipped: set ADMIN_PASSWORD to create the default admin.")
        return
    email = os.environ.get("ADMIN_EMAIL", "admin@moviestream.com").lower()

    with app.app_context():
        if User.query.first() is not None:
            return  # Already have users, don't touch anything.

        # NOTE: "admin.local" and similar reserved-looking TLDs are
        # rejected by the email_validator library used for the Email()
        # form validator (it treats them as special-use/reserved
        # domains). Using a normal-looking .com address avoids that,
        # even though the domain doesn't need to actually exist for
        # local login to work (WTForms only checks syntax, not
        # deliverability).
        admin = User(username="admin", email=email, is_admin=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()


def migrate_movies_out_of_static(app):
    """
    Security fix: movie/trailer files used to live under static/movies/,
    which Flask serves to anyone with zero authentication -- any video
    was reachable at a guessable public URL regardless of login. They
    now live under media/movies/ (outside static/), served only through
    the login-gated /watch/... routes.

    This one-time migration moves any files still sitting in the old
    static/movies/ location over to the new media/movies/ folder, so
    existing installs (movies already uploaded before this fix) keep
    working without needing to be re-uploaded. Database rows are
    unaffected -- video_path/trailer_path only ever stored the bare
    filename, never the folder, so no DB changes are needed.

    Idempotent: safe to call on every startup. Does nothing once the
    old folder is empty (already migrated, or a fresh install that
    never had the old folder).
    """
    import os
    import shutil

    old_folder = os.path.join(os.path.dirname(__file__), "static", "movies")
    new_folder = app.config["MOVIE_FOLDER"]

    if not os.path.isdir(old_folder):
        return  # Fresh install, nothing to migrate.

    os.makedirs(new_folder, exist_ok=True)
    moved = 0
    for filename in os.listdir(old_folder):
        if filename == ".gitkeep":
            continue
        old_path = os.path.join(old_folder, filename)
        new_path = os.path.join(new_folder, filename)
        if os.path.isfile(old_path) and not os.path.exists(new_path):
            shutil.move(old_path, new_path)
            moved += 1

    if moved:
        print(f"[migrate_movies_out_of_static] Moved {moved} file(s) from "
              f"static/movies/ to media/movies/ (now access-controlled).")
