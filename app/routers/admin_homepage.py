from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from ..admin_common import redirect_with_message, render_admin
from ..auth import require_admin, verify_csrf
from ..db import get_db
from ..models_db import HomepageSection, HomepageSectionItem, Product

router = APIRouter(prefix="/admin/homepage", tags=["admin-homepage"])


@router.get("")
def list_sections(request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    sections = db.query(HomepageSection).order_by(HomepageSection.sort_order).all()
    return render_admin(request, "homepage_list.html", {"sections": sections}, session=session)


@router.get("/{key}/edit")
def edit_section_form(key: str, request: Request, db: Session = Depends(get_db), session=Depends(require_admin)):
    section = (
        db.query(HomepageSection)
        .options(joinedload(HomepageSection.items))
        .filter(HomepageSection.key == key)
        .first()
    )
    if not section:
        raise HTTPException(status_code=404, detail="Homepage section not found")
    selected_ids = {item.product_id: item.sort_order for item in section.items}
    products = db.query(Product).filter(Product.published.is_(True)).order_by(Product.name).all()
    return render_admin(request, "homepage_form.html", {
        "section": section, "products": products, "selected_ids": selected_ids,
    }, session=session)


@router.post("/{key}/edit")
async def update_section(
    key: str,
    request: Request,
    db: Session = Depends(get_db),
    session=Depends(require_admin),
):
    form = await request.form()
    verify_csrf(request, session, form.get("csrf_token"))

    section = db.query(HomepageSection).filter(HomepageSection.key == key).first()
    if not section:
        raise HTTPException(status_code=404, detail="Homepage section not found")

    section.enabled = bool(form.get("enabled"))
    section.heading = (form.get("heading") or "").strip() or None
    section.description = (form.get("description") or "").strip() or None
    section.cta_label = (form.get("cta_label") or "").strip() or None
    section.cta_url = (form.get("cta_url") or "").strip() or None

    # Dynamic per-product fields: include_<id> checkbox, order_<id> number.
    chosen = []
    for key_name, value in form.multi_items():
        if key_name.startswith("include_"):
            try:
                product_id = int(key_name.replace("include_", ""))
            except ValueError:
                continue
            order_raw = form.get(f"order_{product_id}", "0")
            try:
                order = int(order_raw)
            except (TypeError, ValueError):
                order = 0
            chosen.append((product_id, order))

    chosen.sort(key=lambda t: t[1])

    db.query(HomepageSectionItem).filter(HomepageSectionItem.section_id == section.id).delete()
    for order, (product_id, _) in enumerate(chosen):
        db.add(HomepageSectionItem(section_id=section.id, product_id=product_id, sort_order=order))

    db.commit()
    return redirect_with_message(f"/admin/homepage/{key}/edit", success="Homepage section saved.")
