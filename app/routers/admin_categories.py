from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session

from ..admin_common import redirect_with_message, render_admin
from ..auth import require_admin, verify_csrf
from ..db import get_db
from ..models_db import Category, Product
from ..uploads import delete_image, save_image
from ..utils import slugify, unique_slug

router = APIRouter(prefix="/admin/categories", tags=["admin-categories"])


@router.get("")
def list_categories(request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
    counts = {c.id: db.query(Product).filter(Product.category_id == c.id).count() for c in categories}
    return render_admin(request, "categories_list.html", {"categories": categories, "counts": counts}, session=session)


@router.get("/new")
def new_category_form(request: Request, session=Depends(require_admin)):
    return render_admin(request, "category_form.html", {"category": None}, session=session)


@router.post("/new")
async def create_category(
    request: Request,
    session=Depends(require_admin),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    name: str = Form(...),
    slug: str = Form(""),
    gender: str = Form(""),
    description: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    active: Optional[str] = Form(None),
    sort_order: int = Form(0),
    image_file: UploadFile = File(default=None),
):
    verify_csrf(request, session, csrf_token)
    if not name.strip():
        return redirect_with_message("/admin/categories/new", error="Category name is required.")

    base_slug = slugify(slug or name)
    final_slug = unique_slug(base_slug, lambda s: db.query(Category).filter(Category.slug == s).first() is not None)

    image_path = None
    if image_file and image_file.filename:
        image_path, _, _ = save_image(image_file, "category")

    category = Category(
        name=name.strip(), slug=final_slug, gender=gender or None,
        description=description.strip() or None, image=image_path,
        seo_title=seo_title.strip() or None, seo_description=seo_description.strip() or None,
        active=bool(active), sort_order=sort_order,
    )
    db.add(category)
    db.commit()
    return redirect_with_message("/admin/categories", success=f"Category \u201c{category.name}\u201d created.")


@router.get("/{category_id}/edit")
def edit_category_form(category_id: int, request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return render_admin(request, "category_form.html", {"category": category}, session=session)


@router.post("/{category_id}/edit")
async def update_category(
    category_id: int,
    request: Request,
    session=Depends(require_admin),
    db: Session = Depends(get_db),
    csrf_token: str = Form(...),
    name: str = Form(...),
    slug: str = Form(""),
    gender: str = Form(""),
    description: str = Form(""),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    active: Optional[str] = Form(None),
    sort_order: int = Form(0),
    image_file: UploadFile = File(default=None),
):
    verify_csrf(request, session, csrf_token)
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if not name.strip():
        return redirect_with_message(f"/admin/categories/{category_id}/edit", error="Category name is required.")

    new_slug = slugify(slug or name)
    if new_slug != category.slug:
        new_slug = unique_slug(
            new_slug,
            lambda s: db.query(Category).filter(Category.slug == s, Category.id != category_id).first() is not None,
        )

    if image_file and image_file.filename:
        new_path, _, _ = save_image(image_file, "category")
        if category.image:
            delete_image(category.image)
        category.image = new_path

    category.name = name.strip()
    category.slug = new_slug
    category.gender = gender or None
    category.description = description.strip() or None
    category.seo_title = seo_title.strip() or None
    category.seo_description = seo_description.strip() or None
    category.active = bool(active)
    category.sort_order = sort_order
    db.commit()
    return redirect_with_message(f"/admin/categories/{category_id}/edit", success="Category saved.")


@router.get("/{category_id}/delete")
def confirm_delete_category(category_id: int, request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    product_count = db.query(Product).filter(Product.category_id == category_id).count()
    other_categories = db.query(Category).filter(Category.id != category_id).order_by(Category.name).all()
    return render_admin(request, "category_delete.html", {
        "category": category, "product_count": product_count, "other_categories": other_categories,
    }, session=session)


@router.post("/{category_id}/delete")
def delete_category(
    category_id: int,
    request: Request,
    csrf_token: str = Form(...),
    reassign_to: str = Form(""),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    products = db.query(Product).filter(Product.category_id == category_id).all()
    if products:
        if not reassign_to:
            return redirect_with_message(
                f"/admin/categories/{category_id}/delete",
                error=f"{len(products)} product(s) are still in this category. Choose a category to move them to first.",
            )
        target = db.query(Category).filter(Category.id == int(reassign_to)).first()
        if not target:
            return redirect_with_message(f"/admin/categories/{category_id}/delete", error="Chosen category not found.")
        for p in products:
            p.category_id = target.id

    if category.image:
        delete_image(category.image)
    db.delete(category)
    db.commit()
    return redirect_with_message("/admin/categories", success=f"Category \u201c{category.name}\u201d deleted.")
