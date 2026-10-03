from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from ..admin_common import redirect_with_message, render_admin
from ..auth import hash_password, require_admin, verify_csrf, verify_password
from ..db import get_db
from ..models_db import BusinessSettings

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


@router.get("")
def settings_form(request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    settings = db.get(BusinessSettings, 1)
    return render_admin(request, "settings.html", {"settings": settings}, session=session)


@router.post("")
def update_settings(
    request: Request,
    db: Session = Depends(get_db),
    session=Depends(require_admin),
    csrf_token: str = Form(...),
    name: str = Form(...),
    legal_name: str = Form(""),
    tagline: str = Form(""),
    description: str = Form(""),
    address_line1: str = Form(""),
    address_line2: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    postal_code: str = Form(""),
    country: str = Form("IN"),
    phone: str = Form(""),
    whatsapp_number: str = Form(""),
    email: str = Form(""),
    opening_hours: str = Form(""),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    google_maps_url: str = Form(""),
    instagram_url: str = Form(""),
    facebook_url: str = Form(""),
    youtube_url: str = Form(""),
    domain: str = Form(""),
):
    verify_csrf(request, session, csrf_token)

    settings = db.get(BusinessSettings, 1)
    if not settings:
        settings = BusinessSettings(id=1)
        db.add(settings)

    settings.name = name.strip()
    settings.legal_name = legal_name.strip() or None
    settings.tagline = tagline.strip()
    settings.description = description.strip()
    settings.address_line1 = address_line1.strip()
    settings.address_line2 = address_line2.strip() or None
    settings.city = city.strip()
    settings.state = state.strip()
    settings.postal_code = postal_code.strip() or None
    settings.country = country.strip() or "IN"
    settings.phone = phone.strip() or None
    settings.whatsapp_number = whatsapp_number.strip() or None
    settings.email = email.strip() or None
    settings.opening_hours = opening_hours.strip()
    settings.latitude = latitude
    settings.longitude = longitude
    settings.google_maps_url = google_maps_url.strip() or None
    settings.instagram_url = instagram_url.strip() or None
    settings.facebook_url = facebook_url.strip() or None
    settings.youtube_url = youtube_url.strip() or None
    settings.domain = domain.strip().rstrip("/")

    db.commit()

    # Also update app/data/business.json for backup/sync consistency
    try:
        import json
        from pathlib import Path
        json_path = Path(__file__).resolve().parent.parent / "data" / "business.json"
        if json_path.exists():
            data = {
                "name": settings.name,
                "legal_name": settings.legal_name,
                "tagline": settings.tagline,
                "description": settings.description,
                "address_line1": settings.address_line1,
                "address_line2": settings.address_line2,
                "city": settings.city,
                "state": settings.state,
                "postal_code": settings.postal_code,
                "country": settings.country,
                "phone": settings.phone,
                "whatsapp_number": settings.whatsapp_number,
                "email": settings.email,
                "opening_hours": settings.opening_hours_list(),
                "latitude": settings.latitude,
                "longitude": settings.longitude,
                "google_maps_url": settings.google_maps_url,
                "instagram_url": settings.instagram_url,
                "facebook_url": settings.facebook_url,
                "youtube_url": settings.youtube_url,
                "domain": settings.domain,
            }
            json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return redirect_with_message("/admin/settings", success="Business settings saved.")


@router.post("/password")
def update_password(
    request: Request,
    db: Session = Depends(get_db),
    session=Depends(require_admin),
    csrf_token: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    verify_csrf(request, session, csrf_token)
    user = session.user
    if not user:
        return redirect_with_message("/admin/settings", error="User account not found.")

    if not verify_password(current_password, user.password_hash):
        return redirect_with_message("/admin/settings", error="Current password is incorrect.")

    if len(new_password) < 10:
        return redirect_with_message("/admin/settings", error="New password must be at least 10 characters long.")

    if new_password != confirm_password:
        return redirect_with_message("/admin/settings", error="New passwords do not match.")

    user.password_hash = hash_password(new_password)
    db.commit()
    return redirect_with_message("/admin/settings", success="Admin password updated successfully.")
