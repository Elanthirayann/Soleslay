import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ..admin_common import redirect_with_message, render_admin
from ..auth import require_admin, verify_csrf
from ..db import get_db
from ..models_db import MediaAsset
from ..uploads import STATIC_ROOT, delete_image, save_image

router = APIRouter(prefix="/admin/media", tags=["admin-media"])

MEDIA_KIND_LABELS = {
    "store_image": "Store photo",
    "store_video": "Store video",
    "hero_poster": "Hero poster image",
    "homepage_media": "Homepage media",
}

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm"}
MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 50 MB


@router.get("")
def list_media(request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    assets = db.query(MediaAsset).order_by(MediaAsset.uploaded_at.desc()).all()
    return render_admin(request, "media.html", {
        "assets": assets, "kind_labels": MEDIA_KIND_LABELS,
    }, session=session)


@router.post("/upload")
def upload_media(
    request: Request,
    csrf_token: str = Form(...),
    kind: str = Form(...),
    alt: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)

    if kind == "store_video":
        if file.content_type not in ALLOWED_VIDEO_TYPES:
            return redirect_with_message("/admin/media", error="Unsupported video type. Please upload MP4 or WEBM.")
        raw = file.file.read(MAX_VIDEO_BYTES + 1)
        if len(raw) > MAX_VIDEO_BYTES:
            return redirect_with_message("/admin/media", error="Video is too large (max 50 MB).")
        ext = "mp4" if file.content_type == "video/mp4" else "webm"
        filename = f"{uuid.uuid4().hex}.{ext}"
        target_dir = STATIC_ROOT / "video"
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / filename).write_bytes(raw)
        web_path = f"/static/video/{filename}"
    elif kind in ("store_image", "hero_poster", "homepage_media"):
        try:
            web_path, _, _ = save_image(file, "store")
        except HTTPException as e:
            return redirect_with_message("/admin/media", error=e.detail)
    else:
        return redirect_with_message("/admin/media", error="Unknown media kind.")

    asset = MediaAsset(filename=file.filename, path=web_path, kind=kind, alt=alt.strip() or None)
    db.add(asset)
    db.commit()
    return redirect_with_message("/admin/media", success="Media uploaded.")


@router.post("/{asset_id}/delete")
def delete_media(
    asset_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    if asset.path.startswith("/static/images/"):
        delete_image(asset.path)
    else:
        rel = asset.path[len("/static/"):]
        full = (STATIC_ROOT / rel).resolve()
        try:
            full.relative_to(STATIC_ROOT.resolve())
            if full.is_file():
                full.unlink()
        except (ValueError, OSError):
            pass

    db.delete(asset)
    db.commit()
    return redirect_with_message("/admin/media", success="Media deleted.")
