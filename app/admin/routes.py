from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Resource, University, Course, Semester, Subject, utcnow
from app.admin.forms import EmptyForm, UniversityForm, CourseForm, SemesterForm, SubjectForm

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


# --- Catalog management (University/Course/Semester/Subject) ---------------
# The only way these rows existed before was seed.py -- there's no Shell/DB
# access on Render's free tier to run it or edit rows by hand, so this is a
# minimal create-only admin UI. No edit/delete: keeping scope to exactly
# what's needed (adding new catalog entries) rather than a full CRUD screen.

def _course_choices():
    return [(c.id, f"{c.name} ({c.university.name})") for c in Course.query.order_by(Course.name).all()]


def _semester_choices():
    return [
        (s.id, f"{s.course.name} Sem {s.number} ({s.course.university.name})")
        for s in Semester.query.order_by(Semester.course_id, Semester.number).all()
    ]


@admin_bp.route("/catalog")
def catalog():
    university_form = UniversityForm()

    course_form = CourseForm()
    course_form.university_id.choices = [(u.id, u.name) for u in University.query.order_by(University.name).all()]

    semester_form = SemesterForm()
    semester_form.course_id.choices = _course_choices()

    subject_form = SubjectForm()
    subject_form.semester_id.choices = _semester_choices()

    return render_template(
        "admin/catalog.html",
        university_form=university_form,
        course_form=course_form,
        semester_form=semester_form,
        subject_form=subject_form,
        universities=University.query.order_by(University.name).all(),
        courses=Course.query.order_by(Course.university_id, Course.name).all(),
        semesters=Semester.query.order_by(Semester.course_id, Semester.number).all(),
        subjects=Subject.query.order_by(Subject.semester_id, Subject.name).all(),
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
            location=(form.location.data or "").strip() or None,
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


@admin_bp.route("/catalog/course", methods=["POST"])
def create_course():
    form = CourseForm()
    form.university_id.choices = [(u.id, u.name) for u in University.query.order_by(University.name).all()]
    if form.validate_on_submit():
        course = Course(
            university_id=form.university_id.data,
            name=form.name.data.strip(),
            full_name=(form.full_name.data or "").strip() or None,
            total_semesters=form.total_semesters.data,
        )
        db.session.add(course)
        db.session.commit()
        flash(f'Added course "{course.name}".', "success")
    else:
        _flash_form_errors(form)
    return redirect(url_for("admin.catalog"))


@admin_bp.route("/catalog/semester", methods=["POST"])
def create_semester():
    form = SemesterForm()
    form.course_id.choices = _course_choices()
    if form.validate_on_submit():
        semester = Semester(course_id=form.course_id.data, number=form.number.data)
        db.session.add(semester)
        try:
            db.session.commit()
            flash(f"Added Semester {semester.number}.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("That course already has a semester with that number.", "error")
    else:
        _flash_form_errors(form)
    return redirect(url_for("admin.catalog"))


@admin_bp.route("/catalog/subject", methods=["POST"])
def create_subject():
    form = SubjectForm()
    form.semester_id.choices = _semester_choices()
    if form.validate_on_submit():
        subject = Subject(
            semester_id=form.semester_id.data,
            name=form.name.data.strip(),
            code=(form.code.data or "").strip() or None,
        )
        db.session.add(subject)
        try:
            db.session.commit()
            flash(f'Added subject "{subject.name}".', "success")
        except IntegrityError:
            db.session.rollback()
            flash("That semester already has a subject with that name.", "error")
    else:
        _flash_form_errors(form)
    return redirect(url_for("admin.catalog"))
