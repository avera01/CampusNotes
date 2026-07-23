from flask import Blueprint, render_template, redirect, url_for, flash, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Resource, Subject, Semester, Course, University, Rating, Comment
from app.resources.forms import UploadForm, RatingForm, CommentForm, EmptyForm
from app.resources.storage import save_resource_file, resource_file_location

resources_bp = Blueprint("resources", __name__, url_prefix="/resources")


@resources_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    form = UploadForm()
    form.university_id.choices = [(u.id, u.name) for u in University.query.order_by(University.name).all()]

    if form.validate_on_submit():
        university = db.session.get(University, form.university_id.data)
        if university is None:
            flash("Please choose a valid university.", "error")
        else:
            course_name = form.course_name.data.strip()
            # Case-insensitive match so "BCA" and "bca" don't end up as two
            # different courses under the same university -- same pattern as
            # the Semester/Subject lookups below, backed by a matching
            # case-insensitive unique index on (university_id, lower(name)).
            course = Course.query.filter(
                Course.university_id == university.id,
                db.func.lower(Course.name) == course_name.lower(),
            ).first()
            if course is None:
                course = Course(university_id=university.id, name=course_name)
                db.session.add(course)
                db.session.flush()  # assigns course.id, needed below for the semester lookup

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
            )
            db.session.add(resource)
            db.session.commit()
            flash("Resource uploaded successfully.", "success")
            return redirect(url_for("resources.detail", resource_id=resource.id))

    return render_template("resources/upload.html", form=form)


@resources_bp.route("/<int:resource_id>")
def detail(resource_id):
    resource = db.session.get(Resource, resource_id) or abort(404)

    rating_form = None
    user_rating = None
    if current_user.is_authenticated and current_user.id != resource.uploader_id:
        rating_form = RatingForm()
        existing = Rating.query.filter_by(user_id=current_user.id, resource_id=resource.id).first()
        if existing:
            user_rating = existing.stars
            rating_form.stars.data = existing.stars

    comments = (
        Comment.query.filter_by(resource_id=resource.id)
        .order_by(Comment.created_at.desc())
        .all()
    )
    comment_form = CommentForm() if current_user.is_authenticated else None
    delete_comment_form = EmptyForm() if current_user.is_authenticated else None

    return render_template(
        "resources/detail.html",
        resource=resource,
        rating_form=rating_form,
        user_rating=user_rating,
        comments=comments,
        comment_form=comment_form,
        delete_comment_form=delete_comment_form,
    )


@resources_bp.route("/<int:resource_id>/rate", methods=["POST"])
@login_required
def rate(resource_id):
    resource = db.session.get(Resource, resource_id) or abort(404)

    if current_user.id == resource.uploader_id:
        flash("You can't rate your own upload.", "error")
        return redirect(url_for("resources.detail", resource_id=resource.id))

    form = RatingForm()
    if form.validate_on_submit():
        # Upsert: one rating per user per resource, backed by the
        # uq_rating_user_resource unique constraint -- same lookup-then-
        # update-or-create pattern as Course/Semester/Subject on upload.
        rating = Rating.query.filter_by(user_id=current_user.id, resource_id=resource.id).first()
        if rating is None:
            rating = Rating(user_id=current_user.id, resource_id=resource.id, stars=form.stars.data)
            db.session.add(rating)
        else:
            rating.stars = form.stars.data
        db.session.commit()
        flash("Rating saved.", "success")
    else:
        flash("Invalid rating.", "error")

    return redirect(url_for("resources.detail", resource_id=resource.id))


@resources_bp.route("/<int:resource_id>/download")
def download(resource_id):
    resource = db.session.get(Resource, resource_id) or abort(404)

    resource.download_count += 1
    db.session.commit()

    directory, filename = resource_file_location(current_app.config["UPLOAD_FOLDER"], resource.file_path)
    return send_from_directory(directory, filename, as_attachment=True, download_name=resource.original_filename)


@resources_bp.route("/<int:resource_id>/preview")
def preview(resource_id):
    resource = db.session.get(Resource, resource_id) or abort(404)
    if resource.file_type != "pdf":
        abort(404)

    directory, filename = resource_file_location(current_app.config["UPLOAD_FOLDER"], resource.file_path)
    return send_from_directory(directory, filename, as_attachment=False)


@resources_bp.route("/<int:resource_id>/comments", methods=["POST"])
@login_required
def add_comment(resource_id):
    resource = db.session.get(Resource, resource_id) or abort(404)

    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(user_id=current_user.id, resource_id=resource.id, body=form.body.data.strip())
        db.session.add(comment)
        db.session.commit()
        flash("Comment posted.", "success")
    else:
        flash("Comment couldn't be posted.", "error")

    return redirect(url_for("resources.detail", resource_id=resource.id))


@resources_bp.route("/<int:resource_id>/comments/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(resource_id, comment_id):
    comment = db.session.get(Comment, comment_id) or abort(404)
    if comment.resource_id != resource_id:
        abort(404)
    if comment.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    form = EmptyForm()
    if form.validate_on_submit():
        db.session.delete(comment)
        db.session.commit()
        flash("Comment deleted.", "info")

    return redirect(url_for("resources.detail", resource_id=resource_id))
