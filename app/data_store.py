"""
Public-site data access layer.

Reads exclusively from the database (via SQLAlchemy models in
models_db.py) and builds the same Pydantic objects (app/models.py) the
existing public templates already expect -- so template code did not need
to change when the storage backend moved from JSON to a real database.

Every function opens its own short-lived DB session and queries fresh on
every call (rather than caching at import time), so admin edits are
reflected on the public site immediately without needing a restart --
including when running multiple worker processes.

Only `published=True` products/categories are ever returned to the public
site. Draft/unpublished content is visible in the admin panel only.
"""
from typing import List, Optional

from sqlalchemy.orm import joinedload

from .db import SessionLocal
from .models import BusinessInfo, Product, ProductImage, ProductSize
from .models_db import (
    Brand as BrandRow,
    BusinessSettings,
    Category as CategoryRow,
    HeroSlide,
    HomepageSection,
    Product as ProductRow,
)


def _to_pydantic_product(row: ProductRow) -> Product:
    images = [ProductImage(src=i.src, alt=i.alt) for i in sorted(row.images, key=lambda i: i.sort_order)]
    if not images:
        # Every product needs at least one image for the Pydantic model /
        # templates to render safely. This should not happen in practice --
        # the admin product form requires at least one image before publish.
        images = [ProductImage(src="/static/images/brand/logo.svg", alt=row.name)]
    sizes = [ProductSize(size=s.size, available=s.available) for s in sorted(row.sizes, key=lambda s: s.sort_order)]
    return Product(
        slug=row.slug,
        name=row.name,
        brand=row.brand_name or "",
        category=row.category_slug or "",
        description=row.description or "",
        price=row.price,
        currency=row.currency,
        sku=row.sku,
        images=images,
        seo_title=row.seo_title or row.name,
        seo_description=row.seo_description or (row.description or "")[:160],
        in_stock=row.in_stock,
        availability_status=row.availability_status,
        is_new=row.is_new,
        is_featured=row.is_featured,
        sizes=sizes,
        gender=row.gender,
    )


def _product_query(db):
    return (
        db.query(ProductRow)
        .options(joinedload(ProductRow.images), joinedload(ProductRow.sizes),
                 joinedload(ProductRow.brand_ref), joinedload(ProductRow.category_ref))
        .filter(ProductRow.published.is_(True))
    )


def get_business() -> BusinessInfo:
    db = SessionLocal()
    try:
        row = db.get(BusinessSettings, 1)
        if not row:
            return BusinessInfo(
                name="Soleslay", tagline="", description="",
                address_line1="", city="", state="",
            )
        return BusinessInfo(
            name=row.name, legal_name=row.legal_name, tagline=row.tagline,
            description=row.description, address_line1=row.address_line1,
            address_line2=row.address_line2, city=row.city, state=row.state,
            postal_code=row.postal_code, country=row.country, phone=row.phone,
            whatsapp_number=row.whatsapp_number, email=row.email,
            opening_hours=row.opening_hours_list(), latitude=row.latitude,
            longitude=row.longitude, google_maps_url=row.google_maps_url,
            instagram_url=row.instagram_url, facebook_url=row.facebook_url,
            youtube_url=row.youtube_url, domain=row.domain or "https://www.soleslay.in",
        )
    finally:
        db.close()


def get_categories() -> dict:
    """slug -> name, active categories only, in sort order. Same shape the
    templates already expect from the old static CATEGORIES dict."""
    db = SessionLocal()
    try:
        rows = (
            db.query(CategoryRow)
            .filter(CategoryRow.active.is_(True))
            .order_by(CategoryRow.sort_order, CategoryRow.name)
            .all()
        )
        return {r.slug: r.name for r in rows}
    finally:
        db.close()


def get_category_meta(slug: str):
    db = SessionLocal()
    try:
        row = db.query(CategoryRow).filter(CategoryRow.slug == slug, CategoryRow.active.is_(True)).first()
        if row:
            db.expunge(row)
        return row
    finally:
        db.close()


def get_products() -> List[Product]:
    db = SessionLocal()
    try:
        rows = _product_query(db).order_by(ProductRow.ranking, ProductRow.name).all()
        return [_to_pydantic_product(r) for r in rows]
    finally:
        db.close()


def get_product(slug: str) -> Optional[Product]:
    db = SessionLocal()
    try:
        row = _product_query(db).filter(ProductRow.slug == slug).first()
        return _to_pydantic_product(row) if row else None
    finally:
        db.close()


def get_products_by_category(category_slug: str) -> List[Product]:
    db = SessionLocal()
    try:
        rows = (
            _product_query(db)
            .join(CategoryRow, ProductRow.category_id == CategoryRow.id)
            .filter(CategoryRow.slug == category_slug)
            .order_by(ProductRow.ranking, ProductRow.name)
            .all()
        )
        return [_to_pydantic_product(r) for r in rows]
    finally:
        db.close()


def get_featured_products() -> List[Product]:
    db = SessionLocal()
    try:
        rows = _product_query(db).filter(ProductRow.is_featured.is_(True)).order_by(ProductRow.ranking).all()
        return [_to_pydantic_product(r) for r in rows]
    finally:
        db.close()


def get_new_arrivals() -> List[Product]:
    db = SessionLocal()
    try:
        rows = _product_query(db).filter(ProductRow.is_new.is_(True)).order_by(ProductRow.ranking).all()
        return [_to_pydantic_product(r) for r in rows]
    finally:
        db.close()


def get_brands() -> List[str]:
    db = SessionLocal()
    try:
        rows = (
            db.query(BrandRow)
            .filter(BrandRow.active.is_(True))
            .order_by(BrandRow.sort_order, BrandRow.name)
            .all()
        )
        return [r.name for r in rows]
    finally:
        db.close()


def get_brand_showcase() -> List[Product]:
    db = SessionLocal()
    try:
        rows = _product_query(db).order_by(ProductRow.ranking).all()
        seen = {}
        for r in rows:
            if r.brand_ref and r.brand_ref.active and r.brand_name not in seen:
                seen[r.brand_name] = r
        return [_to_pydantic_product(r) for r in seen.values()]
    finally:
        db.close()


def get_products_by_gender(gender: str) -> List[Product]:
    db = SessionLocal()
    try:
        rows = _product_query(db).filter(
            (ProductRow.gender == gender) | (ProductRow.gender == "unisex")
        ).order_by(ProductRow.ranking).all()
        return [_to_pydantic_product(r) for r in rows]
    finally:
        db.close()


def search_products(query: str) -> List[Product]:
    q = (query or "").strip().lower()
    if not q:
        return []
    db = SessionLocal()
    try:
        rows = _product_query(db).order_by(ProductRow.ranking).all()
        matches = []
        for r in rows:
            fields = [r.name, r.brand_name, r.description or "", r.category_ref.name if r.category_ref else ""]
            if r.sku:
                fields.append(r.sku)
            if q in " ".join(fields).lower():
                matches.append(r)
        return [_to_pydantic_product(r) for r in matches]
    finally:
        db.close()


def get_top_picks(limit: int = 20) -> List[Product]:
    db = SessionLocal()
    try:
        rows = _product_query(db).all()

        def sort_key(r: ProductRow):
            return (
                0 if r.is_top_pick else 1,
                0 if r.is_featured else 1,
                0 if r.is_new else 1,
                r.ranking,
                r.brand_name.lower(),
                r.name.lower(),
            )

        rows = sorted(rows, key=sort_key)[:limit]
        return [_to_pydantic_product(r) for r in rows]
    finally:
        db.close()


CURATED_CATEGORY_META = {
    "sneakers": {
        "image": "/static/images/products/jordan-1-low-craft.jpg",
        "tagline": "Hype, Dunks & Street Classics",
        "badge": "8 Styles in Store",
        "num": "01",
    },
    "sports-shoes": {
        "image": "/static/images/products/hoka-speedgoat-trail-black.jpg",
        "tagline": "Performance, Trail & Running",
        "badge": "4 Styles in Store",
        "num": "02",
    },
    "sandals": {
        "image": "/static/images/products/woodland-sandal-tan-3395.png",
        "tagline": "Rugged Straps & All-Day Comfort",
        "badge": "3 Styles in Store",
        "num": "03",
    },
    "boots": {
        "image": "/static/images/products/woodland-utrek-hiking-boot-tan.jpg",
        "tagline": "All-Weather Hiking & Chukka",
        "badge": "2 Styles in Store",
        "num": "04",
    },
}


def get_category_showcase() -> List[dict]:
    db = SessionLocal()
    try:
        cats = (
            db.query(CategoryRow)
            .filter(CategoryRow.active.is_(True))
            .order_by(CategoryRow.sort_order, CategoryRow.name)
            .all()
        )
        showcase = []
        for c in cats:
            products = (
                _product_query(db)
                .filter(ProductRow.category_id == c.id)
                .order_by(ProductRow.ranking)
                .all()
            )
            curated = CURATED_CATEGORY_META.get(c.slug, {})
            image = None
            if c.image:
                image = ProductImage(src=c.image, alt=c.name)
            elif curated.get("image"):
                image = ProductImage(src=curated["image"], alt=c.name)
            elif products and products[0].images:
                first_img = sorted(products[0].images, key=lambda i: i.sort_order)[0]
                image = ProductImage(src=first_img.src, alt=first_img.alt)

            showcase.append({
                "slug": c.slug,
                "name": c.name,
                "count": len(products),
                "image": image,
                "tagline": curated.get("tagline", "Curated Footwear"),
                "badge": curated.get("badge", f"{len(products)} Styles"),
                "num": curated.get("num", f"{len(showcase) + 1:02d}"),
            })
        return showcase
    finally:
        db.close()



def get_all_sizes() -> List[str]:
    db = SessionLocal()
    try:
        rows = _product_query(db).all()
        sizes = set()
        for r in rows:
            sizes.update(s.size for s in r.sizes)
        return sorted(sizes)
    finally:
        db.close()


def get_similar_products(product: Product, limit: int = 6) -> List[Product]:
    db = SessionLocal()
    try:
        rows = _product_query(db).filter(ProductRow.slug != product.slug).all()

        def score(r: ProductRow) -> tuple:
            return (
                0 if r.category_slug == product.category else 1,
                0 if product.gender and r.gender == product.gender else 1,
                0 if r.brand_name == product.brand else 1,
                0 if (r.is_featured or r.is_new) else 1,
                r.brand_name.lower(),
                r.name.lower(),
            )

        rows = sorted(rows, key=score)[:limit]
        return [_to_pydantic_product(r) for r in rows]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Homepage sections & hero (owner-managed merchandising)
# ---------------------------------------------------------------------------

def get_homepage_section(key: str) -> Optional[dict]:
    """Returns {enabled, heading, description, cta_label, cta_url, products}
    for one homepage section, or None if the section doesn't exist yet
    (shouldn't happen once migrate.py has run)."""
    db = SessionLocal()
    try:
        section = (
            db.query(HomepageSection)
            .options(joinedload(HomepageSection.items))
            .filter(HomepageSection.key == key)
            .first()
        )
        if not section:
            return None
        product_rows = []
        for item in sorted(section.items, key=lambda i: i.sort_order):
            row = _product_query(db).filter(ProductRow.id == item.product_id).first()
            if row:
                product_rows.append(row)
        products = [_to_pydantic_product(r) for r in product_rows]
        return {
            "enabled": section.enabled,
            "heading": section.heading,
            "description": section.description,
            "cta_label": section.cta_label,
            "cta_url": section.cta_url,
            "products": products,
        }
    finally:
        db.close()


def get_hero_slides() -> List[dict]:
    """Active hero slides, each carrying a live Product plus the owner's
    slide copy. Falls back to an empty list -- main.py falls back to
    featured/new-arrival products when this is empty."""
    db = SessionLocal()
    try:
        slides = (
            db.query(HeroSlide)
            .filter(HeroSlide.active.is_(True))
            .order_by(HeroSlide.sort_order)
            .all()
        )
        result = []
        for slide in slides:
            row = _product_query(db).filter(ProductRow.id == slide.product_id).first()
            if not row:
                continue
            result.append({
                "product": _to_pydantic_product(row),
                "headline": slide.headline,
                "eyebrow": slide.eyebrow,
                "description": slide.description,
                "cta_label": slide.cta_label,
                "cta_url": slide.cta_url,
            })
        return result
    finally:
        db.close()
