from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Resource, University, utcnow
from app.admin.forms import EmptyForm, UniversityForm

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_admin:
        abort(403)


@admin_bp.route("/")
def dashboard():
    pending = Resource.query.filter_by(is_verified=False).order_by(Resource.created_at.desc()).all()
    verified = Resource.query.filter_by(is_verified=True).order_by(Resource.verified_at.desc()).limit(20).all()
    form = EmptyForm()
    return render_template("admin/dashboard.html", pending=pending, verified=verified, form=form)


@admin_bp.route("/resources/<int:resource_id>/verify", methods=["POST"])
def verify_resource(resource_id):
    form = EmptyForm()
    if not form.validate_on_submit():
        abort(400)

    resource = db.session.get(Resource, resource_id) or abort(404)
    resource.is_verified = True
    resource.verified_by_id = current_user.id
    resource.verified_at = utcnow()
    db.session.commit()
    flash(f'Marked "{resource.title}" as verified.', "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/resources/<int:resource_id>/unverify", methods=["POST"])
def unverify_resource(resource_id):
    form = EmptyForm()
    if not form.validate_on_submit():
        abort(400)

    resource = db.session.get(Resource, resource_id) or abort(404)
    resource.is_verified = False
    resource.verified_by_id = None
    resource.verified_at = None
    db.session.commit()
    flash(f'Removed verification from "{resource.title}".', "info")
    return redirect(url_for("admin.dashboard"))


# --- Catalog management (University only) ----------------------------------
# University is the only catalog level admins manage directly -- a small,
# stable list. Course/Semester/Subject are all free-text, lookup-or-create
# fields on the upload form instead (see resources/routes.py), so there's no
# admin UI for them. No edit/delete for University either: keeping scope to
# exactly what's needed (adding new universities) rather than a full CRUD
# screen -- same rationale as before (no Shell/DB access on Render's free
# tier to run seed.py or edit rows by hand).

@admin_bp.route("/catalog")
def catalog():
    university_form = UniversityForm()
    return render_template(
        "admin/catalog.html",
        university_form=university_form,
        universities=University.query.order_by(University.name).all(),
    )


def _flash_form_errors(form):
    for field_errors in form.errors.values():
        for error in field_errors:
            flash(error, "error")


@admin_bp.route("/catalog/university", methods=["POST"])
def create_university():
    form = UniversityForm()
    if form.validate_on_submit():
        university = University(
            name=form.name.data.strip(),
            code=form.code.data.strip(),
        )
        db.session.add(university)
        try:
            db.session.commit()
            flash(f'Added university "{university.name}".', "success")
        except IntegrityError:
            db.session.rollback()
            flash(f'A university with code "{university.code}" already exists.', "error")
    else:
        _flash_form_errors(form)
    return redirect(url_for("admin.catalog"))
