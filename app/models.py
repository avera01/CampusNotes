"""Database models.

Hierarchy: University -> Course -> Semester -> Subject -> Resource.
A User uploads Resources and optionally belongs to a University/Course
for their own profile display (not part of the browsable hierarchy).
"""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class University(db.Model):
    __tablename__ = "universities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)

    courses = db.relationship("Course", backref="university", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<University {self.code}>"


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)          # e.g. "BCA"
    full_name = db.Column(db.String(150))                    # e.g. "Bachelor of Computer Applications"
    total_semesters = db.Column(db.Integer, default=6)
    university_id = db.Column(db.Integer, db.ForeignKey("universities.id"), nullable=False)

    # Case-insensitive so "BCA" and "bca" can't both get created by the
    # upload form's lookup-or-create -- matches the app-level lower(name)
    # check in resources/routes.py, rather than being a weaker DB backstop.
    __table_args__ = (
        db.Index("uq_course_university_name_ci", university_id, db.func.lower(name), unique=True),
    )

    semesters = db.relationship("Semester", backref="course", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Course {self.name}>"


class Semester(db.Model):
    __tablename__ = "semesters"
    __table_args__ = (db.UniqueConstraint("course_id", "number", name="uq_semester_course_number"),)

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)  # 1, 2, 3...
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)

    subjects = db.relationship("Subject", backref="semester", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Semester {self.number} of course {self.course_id}>"


class Subject(db.Model):
    __tablename__ = "subjects"
    __table_args__ = (db.UniqueConstraint("semester_id", "name", name="uq_subject_semester_name"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)   # e.g. "Data Structures"
    code = db.Column(db.String(20))                    # e.g. "CS301" (optional)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False)

    resources = db.relationship("Resource", backref="subject", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subject {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    # Nullable: accounts created via Google Sign-In have no password.
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="student")  # "student" | "admin"
    # Separate from `role` on purpose: `role` gates admin permissions, `user_type`
    # is just a public "who is this" label (Student/Faculty) shown as a badge.
    # server_default (not just default=) because this landed on an existing table
    # with existing rows -- the NOT NULL ALTER TABLE needs a DB-level default to
    # backfill them, a Python-side default= only applies to new ORM inserts.
    user_type = db.Column(db.String(20), nullable=False, server_default="student")  # "student" | "faculty"
    avatar_path = db.Column(db.String(500), nullable=True)  # relative to UPLOAD_FOLDER/avatars

    # How this account was originally created -- "email" or "google". Set
    # once at creation and never changed afterward; it does NOT gate which
    # login methods work (an "email" account that later signs in with
    # Google on the same address is logged into the same account, not
    # blocked -- see auth.google_callback()).
    auth_provider = db.Column(db.String(20), nullable=False, default="email")
    # Google's stable per-account ID ("sub" claim). Stored for reference;
    # account matching/linking itself is by email, per how this app links
    # a pre-existing email/password account to a later Google login.
    google_sub = db.Column(db.String(255), nullable=True, unique=True)

    # Profile fields -- informational only, not joined for browse/search.
    university_id = db.Column(db.Integer, db.ForeignKey("universities.id"), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    current_semester = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow)

    university = db.relationship("University", foreign_keys=[university_id])
    course = db.relationship("Course", foreign_keys=[course_id])

    uploads = db.relationship(
        "Resource", backref="uploader", lazy=True, foreign_keys="Resource.uploader_id"
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        # Google-only accounts have no password_hash -- there's nothing to
        # check them against, so treat that as "wrong password" rather than
        # letting check_password_hash raise on a None hash.
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email}>"


class Resource(db.Model):
    __tablename__ = "resources"

    RESOURCE_TYPES = ("notes", "pyq", "syllabus")

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.String(300))  # comma-separated, searched via LIKE for MVP

    resource_type = db.Column(db.String(20), nullable=False, default="notes")

    file_path = db.Column(db.String(500), nullable=False)       # path relative to UPLOAD_FOLDER
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)        # pdf, docx, jpg...
    file_size = db.Column(db.Integer)                           # bytes

    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verified_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    is_premium = db.Column(db.Boolean, default=False, nullable=False)

    download_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    verified_by = db.relationship("User", foreign_keys=[verified_by_id])

    def __repr__(self):
        return f"<Resource {self.title}>"
