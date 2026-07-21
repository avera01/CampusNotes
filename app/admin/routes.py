from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Resource, utcnow
from app.admin.forms import EmptyForm

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
