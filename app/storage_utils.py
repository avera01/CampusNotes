"""Low-level local-disk file storage helpers shared by resource uploads and
avatar uploads. Both call save_to_directory() / file_location() so the
collision-avoidance and path-splitting logic isn't duplicated per feature.
"""
import os
from werkzeug.utils import secure_filename


def save_to_directory(file_storage, directory):
    """Save file_storage into directory, renaming on filename collision.

    Returns the full path the file was actually saved to.
    """
    os.makedirs(directory, exist_ok=True)

    filename = secure_filename(file_storage.filename)
    base, ext = os.path.splitext(filename)

    candidate = filename
    counter = 1
    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{base}_{counter}{ext}"
        counter += 1

    full_path = os.path.join(directory, candidate)
    file_storage.save(full_path)
    return full_path


def file_location(upload_folder, relative_path):
    """Split a stored relative_path back into (directory, filename) for send_from_directory."""
    directory = os.path.join(upload_folder, os.path.dirname(relative_path))
    filename = os.path.basename(relative_path)
    return directory, filename
