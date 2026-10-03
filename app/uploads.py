"""
Safe image upload handling for the admin panel.

Guards against the common upload-vector attacks:
* Extension/content-type spoofing — we re-encode every upload through
  Pillow, so a renamed .php/.exe that isn't actually a valid image fails
  to decode and is rejected outright. The file that lands on disk is
  always a freshly re-encoded image, never the visitor's raw bytes.
* Path traversal — filenames are never taken from user input; we always
  generate a fresh random name.
* Oversized files / decompression bombs — size is checked before decode,
  and Pillow's pixel-count guard (Image.MAX_IMAGE_PIXELS) is left enabled.
* Executable payloads disguised as images — re-encoding strips anything
  that isn't valid pixel data (no polyglot files survive).
"""
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

STATIC_ROOT = Path(__file__).parent / "static"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 4000  # reject absurdly large source images outright

# Subdirectories under app/static/images/ for each kind of upload.
UPLOAD_KINDS = {
    "product": "products",
    "category": "categories",
    "brand": "brands",
    "store": "store",
}


def _target_dir(kind: str) -> Path:
    if kind not in UPLOAD_KINDS:
        raise HTTPException(status_code=400, detail="Unknown upload kind.")
    d = STATIC_ROOT / "images" / UPLOAD_KINDS[kind]
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_image(upload: UploadFile, kind: str) -> Tuple[str, int, int]:
    """Validates and saves an uploaded image. Returns (web_path, width, height).
    Raises HTTPException(400) on any validation failure."""
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a JPEG, PNG, or WEBP image.",
        )

    raw = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large (max 5 MB).")
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    import io

    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()  # cheap structural check
        # verify() leaves the file object unusable for a second decode, so reopen.
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="File is not a valid image.")

    width, height = image.size
    if width == 0 or height == 0:
        raise HTTPException(status_code=400, detail="Image has invalid dimensions.")
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(status_code=400, detail=f"Image dimensions must be under {MAX_DIMENSION}px.")

    # Normalize mode & re-encode — this both strips anything non-pixel and
    # guarantees the file on disk is exactly what Pillow decoded, nothing else.
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        image = image.convert("RGBA")
        ext, save_kwargs = "png", {"optimize": True}
    else:
        image = image.convert("RGB")
        ext, save_kwargs = "jpg", {"quality": 85, "optimize": True}

    # Downscale very large (but under the hard cap) images to keep the site fast.
    max_side = 2000
    if max(image.size) > max_side:
        image.thumbnail((max_side, max_side), Image.LANCZOS)

    filename = f"{uuid.uuid4().hex}.{ext}"
    target_dir = _target_dir(kind)
    dest = target_dir / filename
    image.save(dest, **save_kwargs)

    web_path = f"/static/images/{UPLOAD_KINDS[kind]}/{filename}"
    return web_path, image.width, image.height


def delete_image(web_path: str) -> None:
    """Best-effort delete of a previously-uploaded image, given its web path.
    Silently no-ops on missing files or paths outside our upload dirs."""
    if not web_path or not web_path.startswith("/static/images/"):
        return
    rel = web_path[len("/static/"):]
    full = (STATIC_ROOT / rel).resolve()
    try:
        full.relative_to(STATIC_ROOT.resolve())
    except ValueError:
        return  # path traversal attempt — refuse
    if full.is_file():
        try:
            full.unlink()
        except OSError:
            pass
