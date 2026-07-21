"""Single shared instances of Flask extensions.

Kept in their own module (rather than created inside __init__.py) so that
models.py and blueprint modules can import `db` / `login_manager` without
triggering a circular import with the app factory.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
oauth = OAuth()
