from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.base_client.errors import OAuthError

from app.extensions import db, oauth
from app.models import User, University, Course, Resource
from app.auth.forms import SignupForm, LoginForm, ProfileForm, ChangePasswordForm, AvatarForm, EmptyForm
from app.auth.avatar_storage import (
    save_avatar_image,
    remove_avatar_file,
    avatar_file_location,
    avatar_url_path,
    InvalidImageError,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _optional_choices(model):
    """(0, '-- optional --') plus every row of `model`, for University/Course selects."""
    return [(0, "-- optional --")] + [(row.id, row.name) for row in model.query.order_by(model.name).all()]


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = SignupForm()
    form.university_id.choices = _optional_choices(University)
    form.course_id.choices = _optional_choices(Course)

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("An account with that email already exists.", "error")
            return render_template("auth/signup.html", form=form)

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            user_type=form.user_type.data,
            university_id=form.university_id.data or None,
            course_id=form.course_id.data or None,
            current_semester=form.current_semester.data or None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Welcome to CampusNotes!", "success")
        return redirect(url_for("main.home"))

    return render_template("auth/signup.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(next_page or url_for("main.home"))
        flash("Invalid email or password.", "error")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/google")
def google_login():
    """Step 1 of Sign in with Google: redirect to Google's consent screen.
    Authlib generates a random `state` value and stashes it in the Flask
    session here, then checks it matches on the way back in
    google_callback() -- that's the CSRF protection for this flow, and it
    needs no extra code on our end.
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    redirect_uri = url_for("auth.google_callback", _external=True)
    # Always show Google's account picker, even if the browser only has one
    # session -- without this, Google can silently reuse the last-used
    # account instead of letting the user choose/switch.
    return oauth.google.authorize_redirect(redirect_uri, prompt="select_account")


@auth_bp.route("/google/callback")
def google_callback():
    """Step 2: Google redirects back here with a `code` (and the `state`
    from step 1). Exchange the code for tokens, pull the verified profile
    out of the ID token, then look up/create/link a User exactly like the
    password flow does -- Flask-Login doesn't care how the User was found.
    """
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    try:
        # This is also where the `state` value gets checked against the
        # session; Authlib raises OAuthError (MismatchingStateError) if it
        # doesn't match, or if Google reports an error (e.g. user declined).
        token = oauth.google.authorize_access_token()
    except OAuthError:
        flash("Google sign-in didn't complete. Please try again.", "error")
        return redirect(url_for("auth.login"))

    # With the `openid` scope and server_metadata_url configured, Authlib
    # verifies the ID token's signature/issuer/audience/expiry itself and
    # hands back the decoded claims here -- we never handle the raw JWT.
    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        flash("Couldn't get your profile info from Google. Please try again.", "error")
        return redirect(url_for("auth.login"))

    # Google can (rarely) report an email it hasn't itself verified. Trusting
    # an unverified address for account lookup/creation would let someone
    # take over an account just by claiming an email they don't control.
    if not userinfo.get("email_verified"):
        flash("That Google account's email address isn't verified.", "error")
        return redirect(url_for("auth.login"))

    email = userinfo["email"].lower().strip()
    google_sub = userinfo.get("sub")

    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            name=userinfo.get("name") or email.split("@")[0],
            email=email,
            auth_provider="google",
            google_sub=google_sub,
        )
        db.session.add(user)
    elif not user.google_sub:
        # An email/password account already exists for this address -- link
        # it by email instead of creating a duplicate. Their password (if
        # any) is left as-is, so both sign-in methods work from here on.
        user.google_sub = google_sub
    db.session.commit()

    login_user(user)
    flash(f"Welcome, {user.name}!", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/account")
@login_required
def account():
    uploads = (
        Resource.query.filter_by(uploader_id=current_user.id)
        .order_by(Resource.created_at.desc())
        .all()
    )
    return render_template("auth/account.html", uploads=uploads)


@auth_bp.route("/settings")
@login_required
def settings():
    # Theme is applied instantly and persisted client-side (see static/js/theme.js
    # and the theme_cookie context processor) -- no server round-trip needed.
    profile_form = ProfileForm(obj=current_user)
    profile_form.university_id.choices = _optional_choices(University)
    profile_form.course_id.choices = _optional_choices(Course)
    profile_form.university_id.data = current_user.university_id or 0
    profile_form.course_id.data = current_user.course_id or 0

    password_form = ChangePasswordForm()
    avatar_form = AvatarForm()
    remove_avatar_form = EmptyForm()

    return render_template(
        "auth/settings.html",
        profile_form=profile_form,
        password_form=password_form,
        avatar_form=avatar_form,
        remove_avatar_form=remove_avatar_form,
    )


@auth_bp.route("/settings/profile", methods=["POST"])
@login_required
def update_profile():
    form = ProfileForm()
    form.university_id.choices = _optional_choices(University)
    form.course_id.choices = _optional_choices(Course)

    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.user_type = form.user_type.data
        current_user.university_id = form.university_id.data or None
        current_user.course_id = form.course_id.data or None
        current_user.current_semester = form.current_semester.data or None
        db.session.commit()
        flash("Profile updated.", "success")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "error")

    return redirect(url_for("auth.settings"))


@auth_bp.route("/settings/password", methods=["POST"])
@login_required
def update_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "error")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password changed.", "success")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                flash(error, "error")

    return redirect(url_for("auth.settings"))


@auth_bp.route("/settings/avatar", methods=["POST"])
@login_required
def update_avatar():
    """JSON endpoint: receives the already-cropped image blob from
    avatar-crop.js (see static/js/avatar-crop.js), not a raw file picked by
    the user -- the crop/zoom/reposition step happens entirely client-side
    before this ever runs. Called via fetch(), so every response here is
    JSON rather than a redirect -- the frontend updates the page in place.
    """
    form = AvatarForm()
    if not form.validate_on_submit():
        # First error is enough for a single inline message; WTForms already
        # phrases these for end users (bad type, too large, missing file).
        first_error = next(iter(form.errors.values()))[0]
        return jsonify(success=False, error=first_error), 400

    try:
        current_user.avatar_path = save_avatar_image(
            form.avatar.data.read(), current_user, current_app.config["UPLOAD_FOLDER"]
        )
    except InvalidImageError as exc:
        return jsonify(success=False, error=str(exc)), 400

    db.session.commit()
    return jsonify(success=True, avatar_url=avatar_url_path(current_user, current_app.config["UPLOAD_FOLDER"]))


@auth_bp.route("/settings/avatar/remove", methods=["POST"])
@login_required
def remove_avatar():
    form = EmptyForm()
    if form.validate_on_submit():
        remove_avatar_file(current_user, current_app.config["UPLOAD_FOLDER"])
        current_user.avatar_path = None
        db.session.commit()
        flash("Profile picture removed.", "info")
    return redirect(url_for("auth.settings"))


@auth_bp.route("/avatar/<int:user_id>")
def avatar(user_id):
    """Public: profile pictures are shown site-wide (nav, uploader credit, etc.)."""
    user = db.session.get(User, user_id) or abort(404)
    if not user.avatar_path:
        abort(404)
    directory, filename = avatar_file_location(current_app.config["UPLOAD_FOLDER"], user.avatar_path)
    response = send_from_directory(directory, filename)
    # Safe to cache aggressively: avatar_url_path() appends a version query
    # param derived from the file's mtime, so any actual change produces a
    # new URL instead of relying on this cache expiring.
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
