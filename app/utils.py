import re


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def unique_slug(base_slug: str, exists_fn) -> str:
    """Appends -2, -3, ... until exists_fn(slug) returns False.
    exists_fn: callable(slug) -> bool"""
    slug = base_slug or "item"
    if not exists_fn(slug):
        return slug
    n = 2
    while exists_fn(f"{slug}-{n}"):
        n += 1
    return f"{slug}-{n}"
