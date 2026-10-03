from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ..admin_common import redirect_with_message, render_admin
from ..auth import require_admin, verify_csrf
from ..db import get_db
from ..models_db import Brand, Product
from ..uploads import delete_image, save_image
from ..utils import slugify, unique_slug

router = APIRouter(prefix="/admin/brands", tags=["admin-brands"])


@router.get("")
def list_brands(request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    brands = db.query(Brand).order_by(Brand.sort_order, Brand.name).all()
    counts = {b.id: db.query(Product).filter(Product.brand_id == b.id).count() for b in brands}
    return render_admin(request, "brands_list.html", {"brands": brands, "counts": counts}, session=session)


@router.get("/new")
def new_brand_form(request: Request, session=Depends(require_admin)):
    return render_admin(request, "brand_form.html", {"brand": None}, session=session)


@router.post("/new")
async def create_brand(
    request: Request,
    session=Depends(require_admin),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    name: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    active: Optional[str] = Form(None),
    sort_order: int = Form(0),
    image_file: UploadFile = File(default=None),
):
    verify_csrf(request, session, csrf_token)
    if not name.strip():
        return redirect_with_message("/admin/brands/new", error="Brand name is required.")

    base_slug = slugify(slug or name)
    final_slug = unique_slug(base_slug, lambda s: db.query(Brand).filter(Brand.slug == s).first() is not None)

    image_path = None
    if image_file and image_file.filename:
        image_path, _, _ = save_image(image_file, "brand")

    brand = Brand(
        name=name.strip(), slug=final_slug, description=description.strip() or None,
        image=image_path, seo_title=seo_title.strip() or None,
        seo_description=seo_description.strip() or None, active=bool(active), sort_order=sort_order,
    )
    db.add(brand)
    db.commit()
    return redirect_with_message("/admin/brands", success=f"Brand \u201c{brand.name}\u201d created.")


@router.get("/{brand_id}/edit")
def edit_brand_form(brand_id: int, request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return render_admin(request, "brand_form.html", {"brand": brand}, session=session)


@router.post("/{brand_id}/edit")
async def update_brand(
    brand_id: int,
    request: Request,
    session=Depends(require_admin),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    name: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    active: Optional[str] = Form(None),
    sort_order: int = Form(0),
    image_file: UploadFile = File(default=None),
):
    verify_csrf(request, session, csrf_token)
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if not name.strip():
        return redirect_with_message(f"/admin/brands/{brand_id}/edit", error="Brand name is required.")

    new_slug = slugify(slug or name)
    if new_slug != brand.slug:
        new_slug = unique_slug(
            new_slug,
            lambda s: db.query(Brand).filter(Brand.slug == s, Brand.id != brand_id).first() is not None,
        )

    if image_file and image_file.filename:
        new_path, _, _ = save_image(image_file, "brand")
        if brand.image:
            delete_image(brand.image)
        brand.image = new_path

    brand.name = name.strip()
    brand.slug = new_slug
    brand.description = description.strip() or None
    brand.seo_title = seo_title.strip() or None
    brand.seo_description = seo_description.strip() or None
    brand.active = bool(active)
    brand.sort_order = sort_order
    db.commit()
    return redirect_with_message(f"/admin/brands/{brand_id}/edit", success="Brand saved.")


@router.post("/{brand_id}/delete")
def delete_brand(
    brand_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    # Products referencing this brand have brand_id ON DELETE SET NULL at
    # the DB level (see models_db.py) -- they are not deleted, just
    # unlinked, and the admin can reassign them from the product form.
    if brand.image:
        delete_image(brand.image)
    db.delete(brand)
    db.commit()
    return redirect_with_message("/admin/brands", success=f"Brand \u201c{brand.name}\u201d deleted.")
