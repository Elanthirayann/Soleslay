"""
SEO utilities: canonical URL building and JSON-LD structured data generators.
No fake ratings, reviews, prices or availability are ever injected here —
only fields that exist on the actual Product / BusinessInfo models.
"""
import json
from typing import List, Optional

from .models import Product, BusinessInfo, CATEGORIES


def canonical(business: BusinessInfo, path: str) -> str:
    path = path if path.startswith("/") else f"/{path}"
    return f"{business.domain.rstrip('/')}{path}"


def organization_schema(business: BusinessInfo) -> dict:
    same_as = [u for u in [business.instagram_url, business.facebook_url, business.youtube_url] if u]
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": business.name,
        "url": business.domain,
        "logo": f"{business.domain.rstrip('/')}/static/images/brand/logo.png",
    }
    if same_as:
        data["sameAs"] = same_as
    return data


def website_schema(business: BusinessInfo) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": business.name,
        "url": business.domain,
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{business.domain.rstrip('/')}/search?q={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }


def local_business_schema(business: BusinessInfo) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "ShoeStore",
        "name": business.name,
        "description": business.description,
        "url": business.domain,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": business.address_line1
            + (f", {business.address_line2}" if business.address_line2 else ""),
            "addressLocality": business.city,
            "addressRegion": business.state,
            "addressCountry": business.country,
        },
    }
    if business.postal_code and "REPLACE" not in business.postal_code:
        data["address"]["postalCode"] = business.postal_code
    if business.phone and "REPLACE" not in business.phone:
        data["telephone"] = business.phone
    if business.opening_hours and all("REPLACE" not in h for h in business.opening_hours):
        data["openingHours"] = business.opening_hours
    if business.latitude and business.longitude:
        data["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": business.latitude,
            "longitude": business.longitude,
        }
    if business.google_maps_url and "REPLACE" not in business.google_maps_url:
        data["hasMap"] = business.google_maps_url
    return data


def breadcrumb_schema(business: BusinessInfo, items: List[tuple]) -> dict:
    """items: list of (name, path) tuples, in order from home to current page."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": name,
                "item": canonical(business, path),
            }
            for i, (name, path) in enumerate(items)
        ],
    }


SCHEMA_AVAILABILITY = {
    "in_stock": "https://schema.org/InStock",
    "limited": "https://schema.org/LimitedAvailability",
    "out_of_stock": "https://schema.org/OutOfStock",
    "check_availability": "https://schema.org/PreOrder",
}


def product_schema(business: BusinessInfo, product: Product) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": product.description,
        "brand": {"@type": "Brand", "name": product.brand},
        "category": CATEGORIES.get(product.category, product.category),
        "image": [canonical(business, img.src) for img in product.images],
        "url": canonical(business, f"/products/{product.slug}"),
    }
    if product.sku:
        data["sku"] = product.sku
    # Only ever emit an Offer when a real price exists — never a fabricated
    # price just so a Product has an offers block.
    if product.price is not None:
        price_value = product.price
        price_str = str(int(price_value)) if price_value == int(price_value) else str(price_value)
        data["offers"] = {
            "@type": "Offer",
            "priceCurrency": product.currency,
            "price": price_str,
            "availability": SCHEMA_AVAILABILITY[product.availability],
            "url": canonical(business, f"/products/{product.slug}"),
        }
    return data


def collection_page_schema(business: BusinessInfo, name: str, path: str, product_urls: List[str]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": name,
        "url": canonical(business, path),
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": canonical(business, url)}
                for i, url in enumerate(product_urls)
            ],
        },
    }


def to_json_ld(schema: dict) -> str:
    return json.dumps(schema, ensure_ascii=False)