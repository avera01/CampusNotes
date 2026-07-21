from flask import Blueprint, render_template, request, jsonify, redirect, url_for

from app.extensions import db
from app.models import University, Course, Semester, Subject, Resource

main_bp = Blueprint("main", __name__)


def _resource_listing_context(include_search):
    """Shared query-building for the Home (filter-only) and Search
    (keyword + filter) pages -- same filtering/sorting/pagination logic,
    just with the free-text `q` param switched on or off.
    """
    university_id = request.args.get("university_id", type=int)
    course_id = request.args.get("course_id", type=int)
    semester_id = request.args.get("semester_id", type=int)
    query_text = request.args.get("q", "", type=str).strip() if include_search else ""
    sort = request.args.get("sort", "recent")
    page = request.args.get("page", 1, type=int)

    query = (
        Resource.query.join(Subject)
        .join(Semester)
        .join(Course)
        .join(University)
    )

    if university_id:
        query = query.filter(University.id == university_id)
    if course_id:
        query = query.filter(Course.id == course_id)
    if semester_id:
        query = query.filter(Semester.id == semester_id)
    if query_text:
        like = f"%{query_text}%"
        query = query.filter(
            db.or_(Resource.title.ilike(like), Resource.tags.ilike(like), Subject.name.ilike(like))
        )

    if sort == "downloads":
        query = query.order_by(Resource.download_count.desc())
    elif sort == "verified":
        query = query.order_by(Resource.is_verified.desc(), Resource.created_at.desc())
    else:
        query = query.order_by(Resource.created_at.desc())

    pagination = query.paginate(page=page, per_page=15, error_out=False)

    # Server-rendered so filter dropdowns show the right options on page load
    # and on browser-back, and the page still works with JS disabled.
    universities = University.query.order_by(University.name).all()
    courses = Course.query.filter_by(university_id=university_id).order_by(Course.name).all() if university_id else []
    semesters = Semester.query.filter_by(course_id=course_id).order_by(Semester.number).all() if course_id else []

    selected = {
        "university_id": university_id,
        "course_id": course_id,
        "semester_id": semester_id,
        "q": query_text,
        "sort": sort,
    }
    # Used to build prev/next pagination links without repeating every filter by hand.
    filter_args = {k: v for k, v in selected.items() if v}

    return {
        "resources": pagination.items,
        "pagination": pagination,
        "universities": universities,
        "courses": courses,
        "semesters": semesters,
        "selected": selected,
        "filter_args": filter_args,
    }


@main_bp.route("/")
def home():
    """Home page: every uploaded resource, filterable by University/Course/
    Semester and sortable. Keyword search lives on the Search page.
    """
    context = _resource_listing_context(include_search=False)
    return render_template("main/home.html", **context)


@main_bp.route("/search")
def search():
    """Dedicated search page: keyword search plus the same filters as Home."""
    context = _resource_listing_context(include_search=True)
    return render_template("main/search.html", **context)


@main_bp.route("/about")
def about():
    return render_template("main/about.html")


@main_bp.route("/browse")
def browse():
    """Old URL kept working -- redirects to the Search page."""
    return redirect(url_for("main.search", **request.args))


# --- Cascading-dropdown JSON endpoints -------------------------------------
# Used by vanilla JS (static/js/cascade.js) on the upload/home/search pages so
# selecting a University narrows Course, then Semester, then Subject, without
# a full page reload or a JS framework.

@main_bp.route("/api/courses")
def api_courses():
    university_id = request.args.get("university_id", type=int)
    if not university_id:
        return jsonify([])
    courses = Course.query.filter_by(university_id=university_id).order_by(Course.name).all()
    return jsonify([{"id": c.id, "label": c.name} for c in courses])


@main_bp.route("/api/semesters")
def api_semesters():
    course_id = request.args.get("course_id", type=int)
    if not course_id:
        return jsonify([])
    semesters = Semester.query.filter_by(course_id=course_id).order_by(Semester.number).all()
    return jsonify([{"id": s.id, "label": f"Semester {s.number}"} for s in semesters])


@main_bp.route("/api/subjects")
def api_subjects():
    semester_id = request.args.get("semester_id", type=int)
    if not semester_id:
        return jsonify([])
    subjects = Subject.query.filter_by(semester_id=semester_id).order_by(Subject.name).all()
    return jsonify([{"id": s.id, "label": s.name} for s in subjects])
