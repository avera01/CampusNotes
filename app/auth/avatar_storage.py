"""Local disk storage for user profile pictures.

Unlike resource uploads (app/resources/storage.py), avatars always live at a
FIXED path per user -- uploads/profile_pics/<user_id>.jpg -- and a re-upload
overwrites the previous picture rather than keeping both around. The image
is always normalized to a single standard size/format server-side (see
save_avatar_image()) regardless of what the client cropped/exported, so we
never store huge or inconsistently-sized files.
"""
import io
import os

from flask import url_for
from PIL import Image, ImageOps

from app.storage_utils import file_location

AVATAR_DIRNAME = "profile_pics"
AVATAR_SIZE = (300, 300)
JPEG_QUALITY = 85


class InvalidImageError(Exception):
    """Raised when the uploaded bytes aren't a valid, decodable image."""


def save_avatar_image(file_bytes, user, upload_folder):
    """Process raw uploaded bytes into a standardized profile picture and
    save it, overwriting any previous picture for this user.

    Returns the relative path (relative to upload_folder) to store on
    User.avatar_path. Raises InvalidImageError for corrupt/non-image data
    (this also catches a file with a spoofed image extension, since Pillow
    has to actually decode it, not just trust the filename).
    """
    try:
        # Image.open() is lazy; verify() forces a full decode/integrity
        # check. Pillow's built-in decompression-bomb guard also applies
        # here, rejecting absurdly large images as a side effect.
        Image.open(io.BytesIO(file_bytes)).verify()
    except Exception as exc:
        raise InvalidImageError("That file isn't a valid image.") from exc

    # verify() leaves the image object unusable for further reads, so reopen.
    image = Image.open(io.BytesIO(file_bytes))

    # Phone photos often carry an EXIF "this way up" tag instead of actually
    # being rotated -- without this, sideways/upside-down avatars are a
    # near-guaranteed bug report.
    image = ImageOps.exif_transpose(image)

    if image.mode != "RGB":
        # Flatten any transparency (PNG/WEBP) onto white before saving as
        # JPEG, which has no alpha channel.
        flattened = Image.new("RGB", image.size, (255, 255, 255))
        rgba = image.convert("RGBA")
        flattened.paste(rgba, mask=rgba.split()[-1])
        image = flattened

    # The frontend already sends a square crop at this size -- ImageOps.fit
    # is a safety net for whatever it actually sent, and guarantees every
    # stored avatar is exactly AVATAR_SIZE regardless of the source.
    image = ImageOps.fit(image, AVATAR_SIZE, Image.LANCZOS)

    directory = os.path.join(upload_folder, AVATAR_DIRNAME)
    os.makedirs(directory, exist_ok=True)
    full_path = os.path.join(directory, f"{user.id}.jpg")

    image.save(full_path, format="JPEG", quality=JPEG_QUALITY, optimize=True)

    return os.path.relpath(full_path, upload_folder)


def remove_avatar_file(user, upload_folder):
    """Best-effort delete of the stored file. Safe to call even if it's
    already gone (e.g. removed twice, or never existed).
    """
    if not user.avatar_path:
        return
    full_path = os.path.join(upload_folder, user.avatar_path)
    try:
        os.remove(full_path)
    except FileNotFoundError:
        pass


def avatar_file_location(upload_folder, relative_path):
    return file_location(upload_folder, relative_path)


def avatar_url_path(user, upload_folder):
    """Cache-busted URL for a user's avatar, or None if they don't have one.

    Because re-uploads overwrite the same filename, the URL would otherwise
    never change and browsers (including the current page's own <img>)
    could keep showing a stale cached picture. Appending the file's mtime
    as a query param forces a refetch whenever the file actually changes,
    while still letting us cache the response aggressively (see the
    Cache-Control header set in the avatar() route).
    """
    if not user.avatar_path:
        return None
    full_path = os.path.join(upload_folder, user.avatar_path)
    if not os.path.exists(full_path):
        return None
    version = int(os.path.getmtime(full_path))
    return url_for("auth.avatar", user_id=user.id) + f"?v={version}"
