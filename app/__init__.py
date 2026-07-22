"""Application factory."""
import os
from flask import Flask, request, url_for

from app.config import Config
from app.extensions import db, migrate, login_manager, oauth


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)

    # "Sign in with Google". server_metadata_url points at Google's OpenID
    # Connect discovery document, so Authlib fetches the authorization/token/
    # userinfo endpoint URLs (and Google's signing keys, for verifying the ID
    # token) automatically instead of them being hardcoded here.
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.resources.routes import resources_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_theme():
        # "system" (the default) means no explicit override -- the page CSS
        # falls back to the OS's prefers-color-scheme media query instead.
        return {"theme_cookie": request.cookies.get("theme", "system")}

    from app.auth.avatar_storage import avatar_url_path

    @app.template_global()
    def avatar_url(user):
        """Cache-busted avatar URL for `user`, or None if they have no picture.
        Used by base.html (nav) and settings.html (preview) so both always
        show the freshest picture -- see avatar_url_path()'s docstring for why.
        """
        return avatar_url_path(user, app.config["UPLOAD_FOLDER"])

    @app.template_global()
    def versioned_static(filename):
        """url_for('static', filename=...) with a ?v=<file mtime> query param.

        Without this, editing a JS/CSS file (like fixing a bug in
        avatar-crop.js) doesn't reliably reach users who already have the
        old version cached by their browser -- a plain reload can silently
        keep running stale, already-fixed-on-disk code. No build step or
        manual version bumping needed: the mtime changes automatically
        whenever the file's contents change.
        """
        full_path = os.path.join(app.static_folder, filename)
        try:
            version = int(os.path.getmtime(full_path))
        except OSError:
            version = 0
        return url_for("static", filename=filename) + f"?v={version}"

    # Auto-create any missing tables on startup. This exists because
    # Render's free tier has no Shell access to run a one-off migration
    # command by hand -- gunicorn starting the app is the only hook we get.
    #
    # Safe to run on every restart: db.create_all() only issues CREATE
    # TABLE for tables that don't already exist (it inspects the database
    # first), so existing tables/data are never touched or duplicated.
    # The one edge case is gunicorn running multiple worker processes,
    # each of which calls create_app() independently and could theoretically
    # race to create the same table at once -- if that happens, the loser
    # gets a "table already exists" error even though the outcome (the
    # table exists) is exactly what we want, so that specific error is
    # swallowed (after logging it) rather than crashing that worker.
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            app.logger.exception(
                "db.create_all() raised on startup -- if this is a "
                "\"already exists\" error from a concurrent gunicorn "
                "worker it's harmless; anything else (e.g. can't reach "
                "the database) means DATABASE_URL needs a look."
            )

        # Bootstrap admin promotion, same rationale as db.create_all() above:
        # no Shell access on Render's free tier to run a one-off command, so
        # this runs on every startup instead. Set INITIAL_ADMIN_EMAIL in
        # Render's environment variables (dashboard, not Shell) to the
        # account's email -- it only takes effect once that user has actually
        # signed up/signed in at least once, so it's safe to leave set
        # permanently: it's a no-op once they're already admin, and it
        # doesn't create a user that doesn't exist yet.
        admin_email = app.config.get("INITIAL_ADMIN_EMAIL")
        if admin_email:
            try:
                from app.models import User

                user = User.query.filter_by(email=admin_email.lower().strip()).first()
                if user is None:
                    app.logger.warning(
                        "INITIAL_ADMIN_EMAIL is set to %s but no user with "
                        "that email exists yet -- sign up/sign in with that "
                        "account first, then restart.", admin_email
                    )
                elif user.role != "admin":
                    user.role = "admin"
                    db.session.commit()
                    app.logger.info("Promoted %s to admin via INITIAL_ADMIN_EMAIL.", user.email)
            except Exception:
                app.logger.exception("Admin promotion check raised on startup.")

    return app
