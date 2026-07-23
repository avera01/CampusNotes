from flask import Blueprint, render_template, redirect, url_for, flash, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Resource, Subject, Semester, Course, University
from app.resources.forms import UploadForm
from app.resources.storage import save_resource_file, resource_file_location

resources_bp = Blueprint("resources", __name__, url_prefix="/resources")


def _is_premium_locked(resource):
    """Premium resources are locked for everyone except the uploader and admins,
    since there's no payment/subscription system yet -- this is UI/logic scaffolding
    for a future "unlock via purchase" flow.
    """
    if not resource.is_premium:
        return False
    if not current_user.is_authenticated:
        return True
    return not (current_user.is_admin or current_user.id == resource.uploader_id)


@resources_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    form = UploadForm()

    if form.validate_on_submit():
        course = db.session.get(Course, form.course_id.data)
        if course is None:
            flash("Please choose a valid university/course from the dropdowns.", "error")
        else:
            semester_number = form.semester_number.data
            semester = Semester.query.filter_by(course_id=course.id, number=semester_number).first()
            if semester is None:
                semester = Semester(course_id=course.id, number=semester_number)
                db.session.add(semester)
                db.session.flush()  # assigns semester.id, needed below for the subject lookup

            subject_name = form.subject_name.data.strip()
            # Case-insensitive match so "Data Structures" and "data structures"
            # don't end up as two different subjects under the same semester.
            subject = Subject.query.filter(
                Subject.semester_id == semester.id,
                db.func.lower(Subject.name) == subject_name.lower(),
            ).first()
            if subject is None:
                subject = Subject(semester_id=semester.id, name=subject_name)
                db.session.add(subject)
                db.session.flush()  # assigns subject.id, needed below for the file path

            relative_path, size = save_resource_file(form.file.data, subject, current_app.config["UPLOAD_FOLDER"])
            original_filename = secure_filename(form.file.data.filename)
            ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""

            resource = Resource(
                title=form.title.data.strip(),
                description=(form.description.data or "").strip(),
                tags=(form.tags.data or "").strip(),
                resource_type=form.resource_type.data,
                file_path=relative_path,
                original_filename=original_filename,
                file_type=ext,
                file_size=size,
                subject_id=subject.id,
                uploader_id=current_user.id,
                is_premium=form.is_premium.data,
            )
            db.session.add(resource)
            db.session.commit()
            flash("Resource uploaded successfully.", "success")
            return redirect(url_for("resources.detail", resource_id=resource.id))

    universities = University.query.order_by(University.name).all()
    return render_template("resources/upload.html", form=form, universities=universities)


@resources_bp.route("/<int:resource_id>")
def detail(resource_id):
    resource = db.session.get(Resource, resource_id) or abort(404)
    locked = _is_premium_locked(resource)
    return render_template("resources/detail.html", resource=resource, locked=locked)


@resources_bp.route("/<int:resource_id>/download")
def download(resource_id):
    resource = db.session.get(Resource, resource_id) or abort(404)
    if _is_premium_locked(resource):
        flash("This is premium content and isn't available yet -- payments aren't set up.", "info")
        return redirect(url_for("resources.detail", resource_id=resource.id))

    resource.download_count += 1
    db.session.commit()

    directory, filename = resource_file_location(current_app.config["UPLOAD_FOLDER"], resource.file_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=resource.original_filename)


@resources_bp.route("/<int:resource_id>/preview")
def preview(resource_id):
    resource = db.session.get(Resource, resource_id) or abort(404)
    if _is_premium_locked(resource):
        abort(403)
    if resource.file_type != "pdf":
        abort(404)

    directory, filename = resource_file_location(current_app.config["UPLOAD_FOLDER"], resource.file_path)
    return send_from_directory(directory, filename, as_attachment=False)
