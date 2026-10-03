from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import json

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import seo
from .models import CATEGORY_DESCRIPTIONS
from .data_store import (
    get_business,
    get_categories,
    get_category_meta,
    get_products,
    get_product,
    get_products_by_category,
    get_featured_products,
    get_new_arrivals,
    get_brands,
    get_brand_showcase,
    search_products,
    get_top_picks,
    get_category_showcase,
    get_all_sizes,
    get_similar_products,
    get_homepage_section,
    get_hero_slides,
)
from .db import Base, engine
from .routers.admin_auth import router as admin_auth_router
from .routers.admin_dashboard import router as admin_dashboard_router
from .routers.admin_products import router as admin_products_router
from .routers.admin_categories import router as admin_categories_router
from .routers.admin_brands import router as admin_brands_router
from .routers.admin_homepage import router as admin_homepage_router
from .routers.admin_hero import router as admin_hero_router
from .routers.admin_media import router as admin_media_router
from .routers.admin_settings import router as admin_settings_router

# Make sure every table exists even if `python -m app.migrate` was never
# run (e.g. a brand-new install with no JSON data to migrate at all).
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Soleslay", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/health", tags=["System"])
@app.get("/ping", tags=["System"])
def health():
    """Ultra-lightweight endpoint for Render keep-awake pings and deployment health checks."""
    return {
        "status": "ok",
        "service": "soleslay",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    favicon_path = STATIC_DIR / "images" / "brand" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/x-icon")
    return Response(status_code=204)

app.include_router(admin_auth_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_products_router)
app.include_router(admin_categories_router)
app.include_router(admin_brands_router)
app.include_router(admin_homepage_router)
app.include_router(admin_hero_router)
app.include_router(admin_media_router)
app.include_router(admin_settings_router)


def clean_whatsapp_number(raw: str) -> str:
    if not raw:
        return ""
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"91{digits[1:]}"
    return digits


def whatsapp_link(text: str) -> str:
    business = get_business()
    number = clean_whatsapp_number(business.whatsapp_number)
    return f"https://wa.me/{number}?text={quote(text)}"


def instagram_dm_link(text: str = "") -> str:
    business = get_business()
    url = (business.instagram_url or "").strip()
    handle = ""
    if url:
        clean_url = url.split("?")[0].rstrip("/")
        handle = clean_url.split("/")[-1]
    if not handle or "REPLACE" in handle:
        handle = "soleslay.chennai"
    return f"https://ig.me/m/{handle}"


def canonical_url(path: str) -> str:
    return seo.canonical(get_business(), path)


templates.env.globals.update(
    clean_whatsapp_number=clean_whatsapp_number,
    whatsapp_link=whatsapp_link,
    instagram_dm_link=instagram_dm_link,
    canonical=canonical_url,
    to_json_ld=seo.to_json_ld,
    current_year=datetime.now().year,
)
# Plain jinja2 (unlike Flask's jinja env) ships no `tojson` filter — used
# for small data-attribute payloads like the hero's trending-items ticker.
# Autoescaping still HTML-escapes the quotes when interpolated, so this
# stays safe to drop straight into an HTML attribute.
templates.env.filters["tojson"] = lambda value: json.dumps(value, default=str)


def base_context(request: Request) -> dict:
    """Fresh, per-request business/category/nav context. Passed into every
    public route's context dict (context always wins over env.globals for
    the same key), so concurrent requests never see another request's data
    and admin edits show up on the very next request."""
    business = get_business()
    categories = get_categories()
    featured_or_new = get_featured_products() or get_new_arrivals()
    return {
        "request": request,
        "business": business,
        "categories": categories,
        "mega_menu_products": featured_or_new[:3],
    }


def listing_facets(products):
    """Real filter/sort facets available for a given product list. A facet
    is only ever included in the UI (via these booleans/lists) when at
    least one product in this listing actually has that data -- the
    templates never render a filter with nothing behind it."""
    return {
        "available_brands": sorted({p.brand for p in products}),
        "has_new": any(p.is_new for p in products),
        "has_featured": any(p.is_featured for p in products),
        "has_price": any(p.price is not None for p in products),
    }


# ---------------------------------------------------------------------------
# Core pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=Response)
def home(request: Request):
    ctx = base_context(request)
    business = ctx["business"]

    new_arrivals = get_new_arrivals()
    top_picks = get_top_picks()

    # Hero: owner-curated slides if any exist, else fall back to the same
    # deterministic featured/new-arrival logic the site always used.
    hero_slides = get_hero_slides()
    if not hero_slides:
        hero_products = (get_featured_products() or new_arrivals)[:4]
        hero_slides = [{"product": p, "headline": None, "eyebrow": None, "description": None,
                         "cta_label": None, "cta_url": None} for p in hero_products]

    featured_section = get_homepage_section("featured")
    new_arrivals_section = get_homepage_section("new_arrivals")
    top_picks_section = get_homepage_section("top_picks")
    sneakers_section = get_homepage_section("sneakers_feature")

    featured_products = (
        featured_section["products"] if featured_section and featured_section["enabled"] and featured_section["products"]
        else get_featured_products()
    )
    new_arrivals_display = (
        new_arrivals_section["products"] if new_arrivals_section and new_arrivals_section["enabled"] and new_arrivals_section["products"]
        else new_arrivals
    )
    new_arrivals_gallery = list(new_arrivals_display) if new_arrivals_display else []
    if 0 < len(new_arrivals_gallery) < 8:
        multiplier = (8 + len(new_arrivals_gallery) - 1) // len(new_arrivals_gallery)
        new_arrivals_gallery = (new_arrivals_gallery * multiplier)[:8]

    top_picks_display = (
        top_picks_section["products"] if top_picks_section and top_picks_section["enabled"] and top_picks_section["products"]
        else top_picks
    )
    sneaker_feature = (
        sneakers_section["products"] if sneakers_section and sneakers_section["enabled"] and sneakers_section["products"]
        else get_products_by_category("sneakers")[:5]
    )

    schemas = [
        seo.organization_schema(business),
        seo.website_schema(business),
        seo.local_business_schema(business),
    ]
    if top_picks_display:
        schemas.append(
            seo.collection_page_schema(business, "Top Picks", "/products", [f"/products/{p.slug}" for p in top_picks_display])
        )

    ctx.update({
        "title": f"{business.name} | Shoe Shop in Guduvanchery, Chennai",
        "meta_description": (
            "Soleslay is a footwear store in Guduvanchery, Chennai offering sneakers, "
            "sports shoes, sandals, slippers and boots from Woodland, Nike, Adidas, "
            "Onitsuka Tiger, Converse, Hoka and more."
        ),
        "canonical_path": "/",
        "featured_products": featured_products,
        "hero_slides": hero_slides,
        "hero_products": [s["product"] for s in hero_slides],
        "new_arrivals": new_arrivals_display,
        "new_arrivals_gallery": new_arrivals_gallery,
        "top_picks": top_picks_display,
        "category_showcase": get_category_showcase(),
        "sneaker_feature": sneaker_feature,
        "all_sizes": get_all_sizes(),
        "brands": get_brands(),
        "brand_showcase": get_brand_showcase(),
        "homepage_sections": {
            "featured": featured_section,
            "new_arrivals": new_arrivals_section,
            "top_picks": top_picks_section,
            "sneakers_feature": sneakers_section,
        },
        "json_ld_schemas": schemas,
    })
    return templates.TemplateResponse("index.html", ctx)


@app.get("/products", response_class=Response)
def product_list(request: Request):
    ctx = base_context(request)
    business = ctx["business"]
    categories = ctx["categories"]
    products = get_products()
    urls = [f"/products/{p.slug}" for p in products]
    schema = seo.collection_page_schema(business, "All Footwear", "/products", urls)
    sidebar_categories = [
        {"slug": slug, "name": name, "count": len(get_products_by_category(slug))}
        for slug, name in categories.items()
    ]
    ctx.update({
        "title": f"Shop All Footwear | {business.name}, Guduvanchery",
        "meta_description": (
            "Browse the full Soleslay footwear range in Guduvanchery, Chennai -- sneakers, "
            "sports shoes, sandals and boots. WhatsApp us for availability."
        ),
        "canonical_path": "/products",
        "products": products,
        "page_heading": "All Footwear",
        "category_description": "The full Soleslay catalogue in one place -- sneakers, sports shoes, sandals and boots from Woodland, Nike, Adidas, Onitsuka Tiger, Converse and Hoka.",
        "active_category": None,
        "sidebar_categories": sidebar_categories,
        "breadcrumbs": [("Home", "/"), ("All Footwear", "/products")],
        "json_ld_schemas": [schema, seo.breadcrumb_schema(business, [("Home", "/"), ("All Footwear", "/products")])],
    })
    ctx.update(listing_facets(products))
    return templates.TemplateResponse("product_list.html", ctx)


@app.get("/products/{slug}", response_class=Response)
def product_detail(request: Request, slug: str):
    product = get_product(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    ctx = base_context(request)
    business = ctx["business"]
    categories = ctx["categories"]
    all_products = get_products()

    similar_products = get_similar_products(product, limit=6)
    breadcrumbs = [
        ("Home", "/"),
        (categories.get(product.category, product.category), f"/category/{product.category}"),
        (product.name, f"/products/{product.slug}"),
    ]
    schemas = [
        seo.product_schema(business, product),
        seo.breadcrumb_schema(business, breadcrumbs),
    ]

    more_brand_count = len([p for p in all_products if p.brand == product.brand and p.slug != product.slug])
    more_category_count = len([p for p in all_products if p.category == product.category and p.slug != product.slug])
    collection_links = []
    if more_brand_count:
        collection_links.append((f"More {product.brand}", f"/search?q={quote(product.brand)}"))
    if more_category_count:
        collection_links.append((f"More {categories.get(product.category, product.category)}", f"/category/{product.category}"))
    if get_new_arrivals():
        collection_links.append(("New Arrivals", "/new-arrivals"))
    collection_links.append(("All Footwear", "/products"))

    primary_img_src = product.images[0].src if product.images else None
    ctx.update({
        "title": product.seo_title,
        "meta_description": product.seo_description,
        "canonical_path": f"/products/{product.slug}",
        "product": product,
        "og_image": primary_img_src,
        "og_type": "product",
        "similar_products": similar_products,
        "collection_links": collection_links,
        "breadcrumbs": breadcrumbs,
        "whatsapp_url": whatsapp_link(product.whatsapp_text),
        "json_ld_schemas": schemas,
    })
    return templates.TemplateResponse("product_detail.html", ctx)


@app.get("/new-arrivals", response_class=Response)
def new_arrivals_page(request: Request):
    ctx = base_context(request)
    business = ctx["business"]
    categories = ctx["categories"]
    products = get_new_arrivals()
    breadcrumbs = [("Home", "/"), ("New Arrivals", "/new-arrivals")]
    urls = [f"/products/{p.slug}" for p in products]
    sidebar_categories = [
        {"slug": slug, "name": name, "count": len(get_products_by_category(slug))}
        for slug, name in categories.items()
    ]
    schemas = [
        seo.collection_page_schema(business, "New Arrivals", "/new-arrivals", urls),
        seo.breadcrumb_schema(business, breadcrumbs),
    ]
    ctx.update({
        "title": f"New Arrivals | {business.name}, Guduvanchery",
        "meta_description": (
            f"The latest footwear to land at {business.name} in Guduvanchery, Chennai. "
            "WhatsApp us to check current sizes and availability."
        ),
        "canonical_path": "/new-arrivals",
        "products": products,
        "page_heading": "New Arrivals",
        "category_description": "The newest footwear to land in-store -- WhatsApp us to check current sizes and availability.",
        "active_category": None,
        "sidebar_categories": sidebar_categories,
        "breadcrumbs": breadcrumbs,
        "json_ld_schemas": schemas,
    })
    ctx.update(listing_facets(products))
    return templates.TemplateResponse("product_list.html", ctx)


@app.get("/search", response_class=Response)
def search(request: Request, q: str = ""):
    ctx = base_context(request)
    business = ctx["business"]
    categories = ctx["categories"]
    products = search_products(q)
    sidebar_categories = [
        {"slug": slug, "name": name, "count": len(get_products_by_category(slug))}
        for slug, name in categories.items()
    ]
    heading = f'Results for "{q}"' if q else "Search"
    ctx.update({
        "title": f"{heading} | {business.name}",
        "meta_description": f"Search the {business.name} footwear catalogue in Guduvanchery, Chennai.",
        "canonical_path": "/search",
        "products": products,
        "page_heading": heading,
        "category_description": None,
        "active_category": None,
        "sidebar_categories": sidebar_categories,
        "breadcrumbs": [("Home", "/"), ("Search", "/search")],
        "search_query": q,
        "robots_content": "noindex, follow",
        "json_ld_schemas": [],
    })
    ctx.update(listing_facets(products))
    return templates.TemplateResponse("product_list.html", ctx)


@app.get("/category/{category_slug}", response_class=Response)
def category_page(request: Request, category_slug: str):
    ctx = base_context(request)
    business = ctx["business"]
    categories = ctx["categories"]
    if category_slug not in categories:
        raise HTTPException(status_code=404, detail="Category not found")

    products = get_products_by_category(category_slug)
    category_name = categories[category_slug]
    category_meta = get_category_meta(category_slug)
    breadcrumbs = [("Home", "/"), (category_name, f"/category/{category_slug}")]
    urls = [f"/products/{p.slug}" for p in products]
    sidebar_categories = [
        {"slug": slug, "name": name, "count": len(get_products_by_category(slug))}
        for slug, name in categories.items()
    ]
    schemas = [
        seo.collection_page_schema(business, category_name, f"/category/{category_slug}", urls),
        seo.breadcrumb_schema(business, breadcrumbs),
    ]
    seo_title = (category_meta.seo_title if category_meta and category_meta.seo_title
                 else f"{category_name} in Guduvanchery, Chennai | {business.name}")
    seo_description = (category_meta.seo_description if category_meta and category_meta.seo_description
                        else f"Shop {category_name.lower()} in Guduvanchery, Chennai at {business.name}. "
                             "WhatsApp us to check current sizes and availability.")
    cat_img = category_meta.image if category_meta and category_meta.image else (products[0].images[0].src if products and products[0].images else None)
    ctx.update({
        "title": seo_title,
        "meta_description": seo_description,
        "canonical_path": f"/category/{category_slug}",
        "og_image": cat_img,
        "products": products,
        "page_heading": category_name,
        "category_description": (category_meta.description if category_meta and category_meta.description
                                  else CATEGORY_DESCRIPTIONS.get(category_slug)),
        "active_category": category_slug,
        "sidebar_categories": sidebar_categories,
        "breadcrumbs": breadcrumbs,
        "json_ld_schemas": schemas,
    })
    ctx.update(listing_facets(products))
    return templates.TemplateResponse("product_list.html", ctx)


@app.get("/about", response_class=Response)
def about(request: Request):
    ctx = base_context(request)
    business = ctx["business"]
    ctx.update({
        "title": f"About {business.name} | Shoe Shop in Guduvanchery",
        "meta_description": (
            f"{business.name} is a footwear store in Guduvanchery, Chennai. "
            "Learn about our store, brands and location."
        ),
        "canonical_path": "/about",
        "brands": get_brands(),
        "json_ld_schemas": [seo.organization_schema(business)],
    })
    return templates.TemplateResponse("about.html", ctx)


@app.get("/contact", response_class=Response)
def contact(request: Request):
    ctx = base_context(request)
    business = ctx["business"]
    ctx.update({
        "title": f"Contact & Store Location | {business.name}, Guduvanchery",
        "meta_description": (
            f"Visit {business.name} in Guduvanchery, Chennai, or reach us on WhatsApp for "
            "footwear availability, sizes and store hours."
        ),
        "canonical_path": "/contact",
        "json_ld_schemas": [seo.local_business_schema(business)],
    })
    return templates.TemplateResponse("contact.html", ctx)


# ---------------------------------------------------------------------------
# SEO infrastructure: sitemap.xml and robots.txt
# ---------------------------------------------------------------------------

@app.get("/sitemap.xml")
def sitemap():
    """Dynamically generated sitemap. Only published products/active
    categories are listed -- draft/unpublished content never appears here."""
    business = get_business()
    categories = get_categories()
    products = get_products()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    static_urls = [
        ("/", "1.0", "daily"),
        ("/products", "0.9", "daily"),
        ("/new-arrivals", "0.8", "daily"),
        ("/about", "0.5", "monthly"),
        ("/contact", "0.5", "monthly"),
    ]
    category_urls = [(f"/category/{slug}", "0.8", "weekly") for slug in categories]
    product_urls = [(f"/products/{p.slug}", "0.7", "weekly") for p in products]

    all_urls = static_urls + category_urls + product_urls

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for path, priority, changefreq in all_urls:
        loc = seo.canonical(business, path)
        xml_parts.append(
            f"<url><loc>{loc}</loc><lastmod>{today}</lastmod>"
            f"<changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>"
        )
    xml_parts.append("</urlset>")

    return Response(content="".join(xml_parts), media_type="application/xml")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    sitemap_url = seo.canonical(get_business(), "/sitemap.xml")
    lines = [
        "User-agent: *",
        "Allow: /",
        "Allow: /static/",
        "Disallow: /admin/",
        f"Sitemap: {sitemap_url}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request: Request, exc: StarletteHTTPException):
    if request.url.path.startswith("/admin"):
        # Preserve admin-specific behavior (e.g. the 303 redirect to
        # /admin/login that require_admin() raises) instead of rendering
        # the public 404 page. Re-raising here would escape this handler
        # entirely (no other handler is registered for it), so we build
        # the response directly from the exception instead.
        return PlainTextResponse(str(exc.detail), status_code=exc.status_code, headers=exc.headers)
    if exc.status_code == 404:
        ctx = base_context(request)
        business = ctx["business"]
        ctx.update({
            "title": f"Page Not Found | {business.name}",
            "meta_description": "The page you're looking for doesn't exist.",
            "canonical_path": "/404",
        })
        return templates.TemplateResponse("404.html", ctx, status_code=404)
    raise exc
