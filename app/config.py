"""Application configuration, loaded from environment variables (.env)."""
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me")

    # SQLite by default; point DATABASE_URL at a postgresql:// URI later
    # and no other code changes are needed (SQLAlchemy abstracts the dialect).
    _database_url = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "campusnotes.db")
    )
    # Some hosts (Heroku historically, occasionally Render) hand out
    # postgres:// URLs -- modern SQLAlchemy only accepts postgresql://
    # and raises NoSuchModuleError on the old scheme, so normalize it.
    if _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Local disk storage. Swap for an S3/Cloudinary-backed storage helper
    # later by changing app/resources/storage.py, not the routes that call it.
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(basedir, "app", "uploads"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 20)) * 1024 * 1024

    # "Sign in with Google" -- see README for how to create these in Google
    # Cloud Console. Only ever read here, server-side; never sent to the
    # frontend/templates.
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # If set, that user is (re-)promoted to admin on every startup -- see
    # the promotion check in app/__init__.py. Bootstrap mechanism for hosts
    # like Render's free tier with no Shell access to run a one-off command
    # by hand. Unset (the default) means this does nothing.
    INITIAL_ADMIN_EMAIL = os.environ.get("INITIAL_ADMIN_EMAIL")
