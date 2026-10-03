from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session, joinedload

from ..admin_common import redirect_with_message, render_admin
from ..auth import require_admin, verify_csrf
from ..db import get_db
from ..models_db import Brand, Category, Product, ProductImage, ProductSize
from ..uploads import delete_image, save_image
from ..utils import slugify, unique_slug

router = APIRouter(prefix="/admin/products", tags=["admin-products"])


def _get_product_or_404(db: Session, product_id: int) -> Product:
    product = (
        db.query(Product)
        .options(joinedload(Product.images), joinedload(Product.sizes))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _form_lists(db: Session):
    brands = db.query(Brand).order_by(Brand.name).all()
    categories = db.query(Category).order_by(Category.sort_order, Category.name).all()
    return brands, categories


@router.get("")
def list_products(request: Request, q: str = "", db: Session = Depends(get_db), session=Depends(require_admin)):
    query = db.query(Product).options(joinedload(Product.brand_ref), joinedload(Product.category_ref))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Product.name.ilike(like))
    products = query.order_by(Product.updated_at.desc()).all()
    return render_admin(request, "products_list.html", {"products": products, "q": q}, session=session)


@router.get("/new")
def new_product_form(request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    brands, categories = _form_lists(db)
    return render_admin(request, "product_form.html", {
        "product": None, "brands": brands, "categories": categories,
    }, session=session)


@router.post("/new")
def create_product(
    request: Request,
    db: Session = Depends(get_db),
    session=Depends(require_admin),
    csrf_token: str = Form(...),
    name: str = Form(...),
    slug: str = Form(""),
    brand_id: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    gender: str = Form(""),
    product_type: str = Form(""),
    description: str = Form(""),
    sku: str = Form(""),
    price: Optional[float] = Form(None),
    currency: str = Form("INR"),
    in_stock: Optional[str] = Form(None),
    availability_status: str = Form(""),
    is_new: Optional[str] = Form(None),
    is_featured: Optional[str] = Form(None),
    is_hot_sale: Optional[str] = Form(None),
    is_best_seller: Optional[str] = Form(None),
    is_top_pick: Optional[str] = Form(None),
    ranking: int = Form(0),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    published: Optional[str] = Form(None),
):
    verify_csrf(request, session, csrf_token)

    if not name.strip():
        return redirect_with_message("/admin/products/new", error="Product name is required.")

    base_slug = slugify(slug or name)
    final_slug = unique_slug(base_slug, lambda s: db.query(Product).filter(Product.slug == s).first() is not None)

    product = Product(
        slug=final_slug,
        name=name.strip(),
        brand_id=brand_id or None,
        category_id=category_id or None,
        gender=gender or None,
        product_type=product_type.strip() or None,
        description=description.strip(),
        sku=sku.strip() or None,
        price=price,
        currency=currency.strip() or "INR",
        in_stock=bool(in_stock),
        availability_status=availability_status or None,
        is_new=bool(is_new),
        is_featured=bool(is_featured),
        is_hot_sale=bool(is_hot_sale),
        is_best_seller=bool(is_best_seller),
        is_top_pick=bool(is_top_pick),
        ranking=ranking,
        seo_title=seo_title.strip() or None,
        seo_description=seo_description.strip() or None,
        published=bool(published),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return redirect_with_message(f"/admin/products/{product.id}/edit", success="Product created. Now add at least one image before publishing.")


@router.get("/{product_id}/edit")
def edit_product_form(product_id: int, request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    product = _get_product_or_404(db, product_id)
    brands, categories = _form_lists(db)
    return render_admin(request, "product_form.html", {
        "product": product, "brands": brands, "categories": categories,
    }, session=session)


@router.post("/{product_id}/edit")
def update_product(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    session=Depends(require_admin),
    csrf_token: str = Form(...),
    name: str = Form(...),
    slug: str = Form(""),
    brand_id: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    gender: str = Form(""),
    product_type: str = Form(""),
    description: str = Form(""),
    sku: str = Form(""),
    price: Optional[float] = Form(None),
    currency: str = Form("INR"),
    in_stock: Optional[str] = Form(None),
    availability_status: str = Form(""),
    is_new: Optional[str] = Form(None),
    is_featured: Optional[str] = Form(None),
    is_hot_sale: Optional[str] = Form(None),
    is_best_seller: Optional[str] = Form(None),
    is_top_pick: Optional[str] = Form(None),
    ranking: int = Form(0),
    seo_title: str = Form(""),
    seo_description: str = Form(""),
    published: Optional[str] = Form(None),
):
    verify_csrf(request, session, csrf_token)
    product = _get_product_or_404(db, product_id)

    if not name.strip():
        return redirect_with_message(f"/admin/products/{product_id}/edit", error="Product name is required.")

    new_slug = slugify(slug or name)
    if new_slug != product.slug:
        new_slug = unique_slug(
            new_slug,
            lambda s: db.query(Product).filter(Product.slug == s, Product.id != product_id).first() is not None,
        )

    if product.published and not bool(published) and not product.images:
        pass  # allowed: owner may unpublish anytime regardless of images

    if bool(published) and not product.images:
        return redirect_with_message(
            f"/admin/products/{product_id}/edit",
            error="Add at least one image before publishing this product.",
        )

    product.slug = new_slug
    product.name = name.strip()
    product.brand_id = brand_id or None
    product.category_id = category_id or None
    product.gender = gender or None
    product.product_type = product_type.strip() or None
    product.description = description.strip()
    product.sku = sku.strip() or None
    product.price = price
    product.currency = currency.strip() or "INR"
    product.in_stock = bool(in_stock)
    product.availability_status = availability_status or None
    product.is_new = bool(is_new)
    product.is_featured = bool(is_featured)
    product.is_hot_sale = bool(is_hot_sale)
    product.is_best_seller = bool(is_best_seller)
    product.is_top_pick = bool(is_top_pick)
    product.ranking = ranking
    product.seo_title = seo_title.strip() or None
    product.seo_description = seo_description.strip() or None
    product.published = bool(published)
    db.commit()
    return redirect_with_message(f"/admin/products/{product_id}/edit", success="Product saved.")


@router.post("/{product_id}/delete")
def delete_product(
    product_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    product = _get_product_or_404(db, product_id)
    for image in product.images:
        delete_image(image.src)
    db.delete(product)
    db.commit()
    return redirect_with_message("/admin/products", success=f"Deleted \u201c{product.name}\u201d.")


@router.post("/{product_id}/toggle-publish")
def toggle_product_publish(
    product_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    product = _get_product_or_404(db, product_id)
    if not product.published and not product.images:
        return redirect_with_message(
            "/admin/products",
            error=f"Cannot publish \u201c{product.name}\u201d: add at least one image first.",
        )
    product.published = not product.published
    db.commit()
    status_label = "published" if product.published else "unpublished (draft)"
    return redirect_with_message("/admin/products", success=f"\u201c{product.name}\u201d is now {status_label}.")


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

@router.post("/{product_id}/images/upload")
async def upload_images(
    product_id: int,
    request: Request,
    csrf_token: str = Form(...),
    files: List[UploadFile] = File(default_factory=list),
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    product = _get_product_or_404(db, product_id)

    uploads = [f for f in files if getattr(f, "filename", "")]
    if not uploads:
        return redirect_with_message(f"/admin/products/{product_id}/edit", error="No files selected.")

    next_order = max([i.sort_order for i in product.images], default=-1) + 1
    saved = 0
    errors = []
    for f in uploads:
        try:
            web_path, _, _ = save_image(f, "product")
        except HTTPException as e:
            errors.append(f"{f.filename}: {e.detail}")
            continue
        is_primary = len(product.images) == 0 and saved == 0
        db.add(ProductImage(
            product_id=product.id, src=web_path, alt=product.name,
            sort_order=next_order, is_primary=is_primary,
        ))
        next_order += 1
        saved += 1
    db.commit()

    if errors and not saved:
        return redirect_with_message(f"/admin/products/{product_id}/edit", error="; ".join(errors))
    msg = f"{saved} image(s) uploaded."
    if errors:
        msg += f" Skipped: {'; '.join(errors)}"
    return redirect_with_message(f"/admin/products/{product_id}/edit", success=msg)


@router.post("/{product_id}/images/{image_id}/alt")
def update_image_alt(
    product_id: int, image_id: int, request: Request,
    csrf_token: str = Form(...), alt: str = Form(""),
    db: Session = Depends(get_db), session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    image = db.query(ProductImage).filter(ProductImage.id == image_id, ProductImage.product_id == product_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    image.alt = alt.strip()
    db.commit()
    return redirect_with_message(f"/admin/products/{product_id}/edit", success="Image alt text updated.")


@router.post("/{product_id}/images/{image_id}/primary")
def set_primary_image(
    product_id: int, image_id: int, request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db), session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    product = _get_product_or_404(db, product_id)
    for img in product.images:
        img.is_primary = (img.id == image_id)
    db.commit()
    return redirect_with_message(f"/admin/products/{product_id}/edit", success="Primary image updated.")


@router.post("/{product_id}/images/{image_id}/move")
def move_image(
    product_id: int, image_id: int, request: Request,
    csrf_token: str = Form(...), direction: str = Form(...),
    db: Session = Depends(get_db), session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    product = _get_product_or_404(db, product_id)
    images = sorted(product.images, key=lambda i: i.sort_order)
    idx = next((i for i, im in enumerate(images) if im.id == image_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Image not found")
    swap_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap_idx < len(images):
        images[idx].sort_order, images[swap_idx].sort_order = images[swap_idx].sort_order, images[idx].sort_order
        db.commit()
    return redirect_with_message(f"/admin/products/{product_id}/edit")


@router.post("/{product_id}/images/{image_id}/delete")
def delete_product_image(
    product_id: int, image_id: int, request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db), session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    image = db.query(ProductImage).filter(ProductImage.id == image_id, ProductImage.product_id == product_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    was_primary = image.is_primary
    delete_image(image.src)
    db.delete(image)
    db.flush()
    if was_primary:
        remaining = (
            db.query(ProductImage)
            .filter(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order)
            .first()
        )
        if remaining:
            remaining.is_primary = True
    db.commit()
    return redirect_with_message(f"/admin/products/{product_id}/edit", success="Image deleted.")


# ---------------------------------------------------------------------------
# Sizes
# ---------------------------------------------------------------------------

@router.post("/{product_id}/sizes/add")
def add_size(
    product_id: int, request: Request,
    csrf_token: str = Form(...), size: str = Form(...), available: Optional[str] = Form(None),
    db: Session = Depends(get_db), session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    product = _get_product_or_404(db, product_id)
    size = size.strip()
    if not size:
        return redirect_with_message(f"/admin/products/{product_id}/edit", error="Enter a size value.")
    if any(s.size.lower() == size.lower() for s in product.sizes):
        return redirect_with_message(f"/admin/products/{product_id}/edit", error="That size is already listed.")
    next_order = max([s.sort_order for s in product.sizes], default=-1) + 1
    db.add(ProductSize(product_id=product.id, size=size, available=bool(available), sort_order=next_order))
    db.commit()
    return redirect_with_message(f"/admin/products/{product_id}/edit", success=f"Size {size} added.")


@router.post("/{product_id}/sizes/{size_id}/toggle")
def toggle_size(
    product_id: int, size_id: int, request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db), session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    size = db.query(ProductSize).filter(ProductSize.id == size_id, ProductSize.product_id == product_id).first()
    if not size:
        raise HTTPException(status_code=404, detail="Size not found")
    size.available = not size.available
    db.commit()
    return redirect_with_message(f"/admin/products/{product_id}/edit")


@router.post("/{product_id}/sizes/{size_id}/delete")
def delete_size(
    product_id: int, size_id: int, request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db), session=Depends(require_admin),
):
    verify_csrf(request, session, csrf_token)
    size = db.query(ProductSize).filter(ProductSize.id == size_id, ProductSize.product_id == product_id).first()
    if not size:
        raise HTTPException(status_code=404, detail="Size not found")
    db.delete(size)
    db.commit()
    return redirect_with_message(f"/admin/products/{product_id}/edit", success="Size removed.")
