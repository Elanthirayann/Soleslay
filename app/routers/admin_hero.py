from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from ..admin_common import redirect_with_message, render_admin
from ..auth import require_admin, verify_csrf
from ..db import get_db
from ..models_db import HeroSlide, Product

router = APIRouter(prefix="/admin/hero", tags=["admin-hero"])


@router.get("")
def list_hero_slides(request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    slides = (
        db.query(HeroSlide)
        .options(joinedload(HeroSlide.product))
        .order_by(HeroSlide.sort_order)
        .all()
    )
    products = db.query(Product).filter(Product.published.is_(True)).order_by(Product.name).all()
    return render_admin(request, "hero.html", {"slides": slides, "products": products}, session=session)


@router.post("/new")
def create_hero_slide(
    request: Request,
    csrf_token: str = Form(...),
    product_id: int = Form(...),
    headline: str = Form(""),
    eyebrow: str = Form(""),
    description: str = Form(""),
    cta_label: str = Form(""),
    cta_url: str = Form(""),
    active: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return redirect_with_message("/admin/hero", error="Choose a valid product for the hero slide.")

    next_order = (db.query(HeroSlide).count())
    slide = HeroSlide(
        product_id=product.id, headline=headline.strip() or None, eyebrow=eyebrow.strip() or None,
        description=description.strip() or None, cta_label=cta_label.strip() or None,
        cta_url=cta_url.strip() or None, active=bool(active), sort_order=next_order,
    )
    db.add(slide)
    db.commit()
    return redirect_with_message("/admin/hero", success="Hero slide added.")


@router.post("/{slide_id}/edit")
def update_hero_slide(
    slide_id: int,
    request: Request,
    csrf_token: str = Form(...),
    product_id: int = Form(...),
    headline: str = Form(""),
    eyebrow: str = Form(""),
    description: str = Form(""),
    cta_label: str = Form(""),
    cta_url: str = Form(""),
    active: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    slide = db.query(HeroSlide).filter(HeroSlide.id == slide_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail="Hero slide not found")
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return redirect_with_message("/admin/hero", error="Choose a valid product for the hero slide.")

    slide.product_id = product.id
    slide.headline = headline.strip() or None
    slide.eyebrow = eyebrow.strip() or None
    slide.description = description.strip() or None
    slide.cta_label = cta_label.strip() or None
    slide.cta_url = cta_url.strip() or None
    slide.active = bool(active)
    db.commit()
    return redirect_with_message("/admin/hero", success="Hero slide updated.")


@router.post("/{slide_id}/move")
def move_hero_slide(
    slide_id: int,
    request: Request,
    csrf_token: str = Form(...),
    direction: str = Form(...),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    slides = db.query(HeroSlide).order_by(HeroSlide.sort_order).all()
    idx = next((i for i, s in enumerate(slides) if s.id == slide_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Hero slide not found")
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(slides):
        slides[idx].sort_order, slides[swap_idx].sort_order = slides[swap_idx].sort_order, slides[idx].sort_order
        db.commit()
    return redirect_with_message("/admin/hero")


@router.post("/{slide_id}/delete")
def delete_hero_slide(
    slide_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    slide = db.query(HeroSlide).filter(HeroSlide.id == slide_id).first()
    if not slide:
        raise HTTPException(status_code=404, detail="Hero slide not found")
    db.delete(slide)
    db.commit()
    return redirect_with_message("/admin/hero", success="Hero slide removed.")
