"""
One-time (but safely re-runnable) migration from the old JSON files into
the database.

Usage:
    python -m app.migrate

What it does
------------
1. Creates all tables (if they don't already exist).
2. Seeds Category rows from the fixed CATEGORIES map in app/models.py,
   preserving each category's existing slug.
3. Seeds a Brand row for every distinct brand found in products.json.
4. Imports every product in products.json — preserving slug, images
   (existing file paths under /static/images/products/ are kept as-is,
   nothing is re-uploaded or moved), SEO fields, and all merchandising
   flags (is_new/is_featured).
5. Imports business.json into the single-row BusinessSettings table,
   preserving every field including any placeholder REPLACE_* values
   still in there — nothing is silently dropped or invented.
6. Creates default (initially empty/disabled) homepage sections so the
   admin homepage-management screen has rows to edit from day one.
7. Does NOT delete products.json / business.json. They are left on disk
   untouched as a backup; the running app reads exclusively from the
   database after this script has been run once.

Idempotent: re-running this script will not create duplicate categories,
brands, or products (matched by slug) — it updates them in place instead.
It also will not duplicate homepage sections or overwrite business
settings that have already been edited in the admin panel (pass
--force-business to overwrite business settings from business.json again).
"""
import argparse
import json
import sys
from pathlib import Path

from .db import Base, engine, session_scope
from .models import CATEGORIES as CATEGORY_MAP
from .models_db import (
    Brand,
    BusinessSettings,
    Category,
    HomepageSection,
    Product,
    ProductImage,
    ProductSize,
)

DATA_DIR = Path(__file__).parent / "data"

DEFAULT_HOMEPAGE_SECTIONS = [
    ("hero", "Hero Carousel", "Featured products shown at the very top of the homepage."),
    ("new_arrivals", "New Arrivals", "The latest footwear to land in-store."),
    ("new_releases", "New Releases", "A secondary new-releases strip, if you want one distinct from New Arrivals."),
    ("top_picks", "Top 20 Picks", "The store's curated top picks."),
    ("featured", "Featured Products", "Hand-picked featured products."),
    ("sneakers_feature", "Sneakers Feature", "From Onitsuka Tiger's retro runners to Jordan and Nike classics — Soleslay's sneaker rack is where most of our regulars start looking."),
    ("brand_showcase", "Brand Showcase", "One representative product per brand."),
    ("store_media", "Store Media", "Store photos/video shown on the homepage."),
]


def slugify_brand(name: str) -> str:
    return name.strip().lower().replace(" ", "-").replace("&", "and")


def migrate(force_business: bool = False):
    Base.metadata.create_all(bind=engine)

    with session_scope() as db:
        # --- Categories -----------------------------------------------------
        category_by_slug = {}
        for order, (slug, name) in enumerate(CATEGORY_MAP.items()):
            cat = db.query(Category).filter(Category.slug == slug).first()
            if not cat:
                cat = Category(slug=slug, name=name, sort_order=order)
                db.add(cat)
                db.flush()
            category_by_slug[slug] = cat
        print(f"Categories: {len(category_by_slug)} ready.")

        # --- Products (+ Brands) --------------------------------------------
        products_path = DATA_DIR / "products.json"
        brand_by_name = {}
        product_count = 0
        if products_path.exists():
            raw_products = json.loads(products_path.read_text(encoding="utf-8"))
            for order, item in enumerate(raw_products):
                brand_name = item.get("brand", "").strip()
                if brand_name and brand_name not in brand_by_name:
                    slug = slugify_brand(brand_name)
                    brand = db.query(Brand).filter(Brand.slug == slug).first()
                    if not brand:
                        brand = Brand(name=brand_name, slug=slug, sort_order=len(brand_by_name))
                        db.add(brand)
                        db.flush()
                    brand_by_name[brand_name] = brand

                slug = item["slug"]
                product = db.query(Product).filter(Product.slug == slug).first()
                is_new_product = product is None
                if is_new_product:
                    product = Product(slug=slug)
                    db.add(product)

                product.name = item.get("name", product.name if not is_new_product else "")
                product.brand_id = brand_by_name[brand_name].id if brand_name in brand_by_name else None
                product.category_id = category_by_slug.get(item.get("category")).id if item.get("category") in category_by_slug else None
                product.gender = item.get("gender")
                product.description = item.get("description", "")
                product.sku = item.get("sku")
                product.price = item.get("price")
                product.currency = item.get("currency", "INR")
                product.in_stock = item.get("in_stock", True)
                product.availability_status = item.get("availability_status")
                product.is_new = item.get("is_new", False)
                product.is_featured = item.get("is_featured", False)
                product.seo_title = item.get("seo_title")
                product.seo_description = item.get("seo_description")
                product.published = True
                product.ranking = order

                db.flush()

                if is_new_product:
                    for img_order, img in enumerate(item.get("images", [])):
                        db.add(ProductImage(
                            product_id=product.id,
                            src=img["src"],
                            alt=img.get("alt", ""),
                            sort_order=img_order,
                            is_primary=(img_order == 0),
                        ))
                    for size_order, size in enumerate(item.get("sizes", [])):
                        db.add(ProductSize(
                            product_id=product.id,
                            size=size["size"],
                            available=size.get("available", True),
                            sort_order=size_order,
                        ))
                product_count += 1
            print(f"Products: {product_count} imported/updated. Brands: {len(brand_by_name)}.")
        else:
            print("No products.json found — skipping product import.", file=sys.stderr)

        # --- Business settings ------------------------------------------------
        business_path = DATA_DIR / "business.json"
        existing = db.get(BusinessSettings, 1)
        if business_path.exists() and (existing is None or force_business):
            b = json.loads(business_path.read_text(encoding="utf-8"))
            settings = existing or BusinessSettings(id=1)
            settings.name = b.get("name", "")
            settings.legal_name = b.get("legal_name")
            settings.tagline = b.get("tagline", "")
            settings.description = b.get("description", "")
            settings.address_line1 = b.get("address_line1", "")
            settings.address_line2 = b.get("address_line2")
            settings.city = b.get("city", "")
            settings.state = b.get("state", "")
            settings.postal_code = b.get("postal_code")
            settings.country = b.get("country", "IN")
            settings.phone = b.get("phone")
            settings.whatsapp_number = b.get("whatsapp_number")
            settings.email = b.get("email")
            settings.opening_hours = "\n".join(b.get("opening_hours", []))
            settings.latitude = b.get("latitude")
            settings.longitude = b.get("longitude")
            settings.google_maps_url = b.get("google_maps_url")
            settings.instagram_url = b.get("instagram_url")
            settings.facebook_url = b.get("facebook_url")
            settings.youtube_url = b.get("youtube_url")
            settings.domain = b.get("domain", "")
            if not existing:
                db.add(settings)
            print("Business settings: imported.")
        else:
            print("Business settings: already present, left untouched (use --force-business to re-import).")

        # --- Default homepage sections -----------------------------------------
        created_sections = 0
        for order, (key, label, description) in enumerate(DEFAULT_HOMEPAGE_SECTIONS):
            section = db.query(HomepageSection).filter(HomepageSection.key == key).first()
            if not section:
                db.add(HomepageSection(
                    key=key, label=label, description=description,
                    enabled=True, sort_order=order,
                ))
                created_sections += 1
        print(f"Homepage sections: {created_sections} created (rest already existed).")

    print("\nMigration complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Soleslay JSON data into the database.")
    parser.add_argument(
        "--force-business", action="store_true",
        help="Overwrite existing business settings from business.json even if already migrated.",
    )
    args = parser.parse_args()
    migrate(force_business=args.force_business)
