"""
media.py

Shared file-handling logic for movie uploads: extension validation,
safe unique filenames, SHA-256 hashing for duplicate detection, and
optional automatic metadata extraction (duration, poster frame) via
ffmpeg/ffprobe when they're installed on the host.

Kept as its own top-level module (rather than inside a blueprint)
because both the `movies` blueprint (the upload page) and the `api`
blueprint (the JSON upload endpoint) need the exact same logic --
duplicating it in two places would violate the "avoid duplicate
code" coding standard.
"""

import hashlib
import os
import shutil
import subprocess
import uuid

from flask import current_app
from werkzeug.utils import secure_filename


def _has_ffmpeg():
    """Check once whether ffmpeg/ffprobe are on PATH. Feature is optional."""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def allowed_video(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_VIDEO_EXTENSIONS"]


def allowed_image(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def unique_filename(original_filename):
    """
    Build a collision-proof filename that still keeps a readable
    trace of the original name, e.g. 'my-movie-a1b2c3d4.mp4'.
    """
    safe_name = secure_filename(original_filename) or "file"
    stem, ext = os.path.splitext(safe_name)
    return f"{stem}-{uuid.uuid4().hex[:8]}{ext}"


def hash_file(filepath):
    """SHA-256 of a file's bytes, used to detect duplicate uploads."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def probe_duration_seconds(filepath):
    """
    Return the video's duration in seconds via ffprobe, or None if
    ffprobe isn't installed / the probe fails. Callers must handle
    None gracefully (e.g. fall back to a manually entered runtime).
    """
    if not _has_ffmpeg():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def generate_poster_from_video(video_path, poster_output_path, at_seconds=2):
    """
    Auto-generate a poster image by grabbing a frame from the video
    with ffmpeg. Returns True on success, False if ffmpeg is missing
    or extraction fails (caller then falls back to the CSS
    placeholder card -- never a fake/stock image).
    """
    if not _has_ffmpeg():
        return False
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(at_seconds),
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "3",
                poster_output_path,
            ],
            capture_output=True, timeout=30, check=True,
        )
        return os.path.exists(poster_output_path)
    except (subprocess.SubprocessError, OSError):
        return False


def save_upload(file_storage, destination_folder):
    """
    Save a Werkzeug FileStorage to destination_folder under a unique
    filename. Returns (filename, absolute_path).
    """
    os.makedirs(destination_folder, exist_ok=True)
    filename = unique_filename(file_storage.filename)
    absolute_path = os.path.join(destination_folder, filename)
    file_storage.save(absolute_path)
    return filename, absolute_path


def minutes_from_seconds(seconds):
    """Round a duration in seconds to whole minutes for runtime_minutes."""
    if seconds is None:
        return None
    return max(1, round(seconds / 60))
