"""Local disk storage for uploaded resource files.

Every function here takes/returns plain paths and byte sizes -- callers
(routes) never touch the filesystem directly. To move to S3/Cloudinary
later, reimplement save_resource_file() and resource_file_location() to
talk to that backend and keep returning the same (relative_path, size) /
(directory, filename) shape; no route or template code needs to change.
"""
import os
from werkzeug.utils import secure_filename

from app.storage_utils import save_to_directory, file_location


def _subject_directory(upload_folder, subject):
    """uploads/<university_code>/<course_name>/sem<N>/<subject_name>/"""
    semester = subject.semester
    course = semester.course
    university = course.university

    parts = [
        secure_filename(university.code),
        secure_filename(course.name),
        f"sem{semester.number}",
        secure_filename(subject.name),
    ]
    return os.path.join(upload_folder, *parts)


def save_resource_file(file_storage, subject, upload_folder):
    """Save an uploaded FileStorage under the subject's folder.

    Returns (relative_path, size_bytes) where relative_path is relative to
    upload_folder -- that's what gets stored on Resource.file_path.
    """
    directory = _subject_directory(upload_folder, subject)
    full_path = save_to_directory(file_storage, directory)
    size = os.path.getsize(full_path)
    relative_path = os.path.relpath(full_path, upload_folder)
    return relative_path, size


def resource_file_location(upload_folder, relative_path):
    return file_location(upload_folder, relative_path)
