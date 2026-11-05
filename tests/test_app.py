"""
Regression tests for the security and data-integrity fixes.

Run from the project root:
    python -m unittest discover tests
"""

import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage

from app import create_app
from config import BaseConfig, ProductionConfig
from database import db
from models import Favorite, Genre, Language, Movie, User


def make_config(tmp, **overrides):
    class TestConfig(BaseConfig):
        TESTING = True
        SECRET_KEY = "test-secret"
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        WTF_CSRF_ENABLED = False
        BCRYPT_LOG_ROUNDS = 4
        MEDIA_ROOT = tmp
        MOVIE_FOLDER = os.path.join(tmp, "movies")
        POSTER_FOLDER = os.path.join(tmp, "posters")
        AVATAR_FOLDER = os.path.join(tmp, "avatars")

    for key, value in overrides.items():
        setattr(TestConfig, key, value)
    return TestConfig


class AppTestCase(unittest.TestCase):
    config_overrides = {}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.app = create_app(make_config(self.tmp, **self.config_overrides))
        self.movie_folder = self.app.config["MOVIE_FOLDER"]
        os.makedirs(self.movie_folder)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.genre = Genre(name="Drama")
        self.language = Language(name="English")
        db.session.add_all([self.genre, self.language])
        for name, is_admin in (("admin", True), ("user", False)):
            user = User(username=name, email=f"{name}@example.com", is_admin=is_admin)
            user.set_password("password123")
            db.session.add(user)

        self.write_file("movie.mp4", b"main video")
        self.write_file("movie-trailer-1a2b3c4d.mp4", b"trailer video")
        self.movie = Movie(
            title="Test Movie",
            description="desc",
            release_year=2024,
            runtime_minutes=90,
            video_path="movie.mp4",
            trailer_path="movie-trailer-1a2b3c4d.mp4",
            file_hash="a" * 64,
            genre=self.genre,
            language=self.language,
        )
        db.session.add(self.movie)
        db.session.commit()
        self.movie_id = self.movie.id
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_file(self, name, data):
        path = os.path.join(self.app.config["MOVIE_FOLDER"], name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def login(self, name, next_url=None):
        url = "/login" + (f"?next={next_url}" if next_url else "")
        return self.client.post(
            url, data={"email": f"{name}@example.com", "password": "password123"}
        )


class ApiAuthorizationTests(AppTestCase):
    def write_requests(self):
        return [
            lambda: self.client.patch(f"/api/movies/{self.movie_id}", json={"title": "pwned"}),
            lambda: self.client.delete(f"/api/movies/{self.movie_id}"),
            lambda: self.client.post("/api/movies/scan"),
        ]

    def test_anonymous_cannot_modify_movies(self):
        for send in self.write_requests():
            self.assertEqual(send().status_code, 401)
        self.assertEqual(db.session.get(Movie, self.movie_id).title, "Test Movie")

    def test_non_admin_cannot_modify_movies(self):
        self.login("user")
        for send in self.write_requests():
            self.assertEqual(send().status_code, 403)
        self.assertEqual(db.session.get(Movie, self.movie_id).title, "Test Movie")

    def test_admin_can_patch_movie(self):
        self.login("admin")
        response = self.client.patch(f"/api/movies/{self.movie_id}", json={"title": "New"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["title"], "New")


class LoginRedirectTests(AppTestCase):
    def test_rejects_external_next_urls(self):
        for evil in ("//evil.com", "/\\evil.com", "https://evil.com"):
            self.client = self.app.test_client()
            response = self.login("user", next_url=evil)
            self.assertEqual(response.status_code, 302)
            self.assertNotIn("evil.com", response.headers["Location"], evil)

    def test_allows_local_next_url(self):
        response = self.login("user", next_url=f"/movie/{self.movie_id}")
        self.assertEqual(response.headers["Location"], f"/movie/{self.movie_id}")


class ConfigTests(unittest.TestCase):
    def test_production_requires_secret_key(self):
        class NoSecret(ProductionConfig):
            SECRET_KEY = None
            SQLALCHEMY_DATABASE_URI = "sqlite://"

        with self.assertRaises(RuntimeError):
            create_app(NoSecret)


class CsrfTests(AppTestCase):
    config_overrides = {"WTF_CSRF_ENABLED": True}

    def test_json_api_write_requires_csrf_token(self):
        response = self.client.post("/api/favorites", json={"movie_id": self.movie_id})
        self.assertEqual(response.status_code, 400)


class DeleteMovieTests(AppTestCase):
    def test_delete_removes_favorites_and_files(self):
        user = User.query.filter_by(username="user").first()
        db.session.add(Favorite(user_id=user.id, movie_id=self.movie_id))
        db.session.commit()

        self.login("admin")
        response = self.client.delete(f"/api/movies/{self.movie_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Favorite.query.count(), 0)
        self.assertFalse(os.path.exists(os.path.join(self.movie_folder, "movie.mp4")))

    def test_files_kept_when_commit_fails(self):
        from blueprints.movies.services import delete_movie_and_files

        with mock.patch.object(db.session, "commit", side_effect=RuntimeError("db down")):
            with self.assertRaises(RuntimeError):
                delete_movie_and_files(db.session.get(Movie, self.movie_id))

        self.assertTrue(os.path.exists(os.path.join(self.movie_folder, "movie.mp4")))


class LibraryScanTests(AppTestCase):
    def test_scan_skips_registered_trailers(self):
        self.login("admin")
        response = self.client.post("/api/movies/scan")
        self.assertEqual(response.get_json()["created_count"], 0)

    def test_scan_registers_new_file(self):
        self.write_file("brand-new.mp4", b"new content")
        self.login("admin")
        response = self.client.post("/api/movies/scan")
        self.assertEqual(response.get_json()["created_count"], 1)


class UploadTests(AppTestCase):
    def test_failed_commit_removes_saved_files(self):
        from blueprints.movies.services import create_movie_from_upload

        before = set(os.listdir(self.movie_folder))
        error = IntegrityError("INSERT", {}, Exception("unique"))
        with mock.patch.object(db.session, "commit", side_effect=error):
            with self.assertRaises(IntegrityError):
                create_movie_from_upload(
                    title="Race",
                    description="d",
                    genre_id=self.genre.id,
                    language_id=self.language.id,
                    release_year=2024,
                    runtime_minutes=10,
                    video_file=FileStorage(io.BytesIO(b"unique bytes"), filename="race.mp4"),
                    trailer_file=FileStorage(io.BytesIO(b"trailer bytes"), filename="t.mp4"),
                )

        self.assertEqual(set(os.listdir(self.movie_folder)), before)


if __name__ == "__main__":
    unittest.main()
