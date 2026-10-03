"""
SQLAlchemy ORM models backing the admin CMS.

Kept deliberately separate from app/models.py, which holds the Pydantic
models used to render the public site templates. data_store.py is the
bridge: it queries these ORM models and builds the Pydantic objects the
existing public templates already expect, so the public-facing templates
did not need to change.
"""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    sessions = relationship("AdminSession", back_populates="user", cascade="all, delete-orphan")


class AdminSession(Base):
    """Server-side session. The cookie only ever holds this row's opaque
    `token` — no user data is stored client-side, and deleting the row
    (logout) immediately invalidates the cookie."""
    __tablename__ = "admin_sessions"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True, default=_uuid)
    csrf_token = Column(String(64), nullable=False, default=_uuid)
    user_id = Column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)

    user = relationship("AdminUser", back_populates="sessions")

    @staticmethod
    def new_expiry(hours: int = 12) -> datetime:
        return utcnow() + timedelta(hours=hours)


class LoginAttempt(Base):
    """Backs simple login rate-limiting. Old rows are pruned periodically."""
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True)
    ip_address = Column(String(64), nullable=False, index=True)
    username = Column(String(64), nullable=True)
    success = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(140), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    image = Column(String(500), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    seo_title = Column(String(255), nullable=True)
    seo_description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    products = relationship("Product", back_populates="brand_ref")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    slug = Column(String(140), unique=True, nullable=False, index=True)
    gender = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    image = Column(String(500), nullable=True)
    seo_title = Column(String(255), nullable=True)
    seo_description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    products = relationship("Product", back_populates="category_ref")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)

    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    gender = Column(String(20), nullable=True)  # men | women | unisex | None
    product_type = Column(String(120), nullable=True)
    description = Column(Text, nullable=False, default="")
    sku = Column(String(120), nullable=True)

    price = Column(Float, nullable=True)
    currency = Column(String(8), default="INR", nullable=False)

    in_stock = Column(Boolean, default=True, nullable=False)
    availability_status = Column(String(30), nullable=True)  # in_stock/limited/out_of_stock/check_availability

    is_new = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    is_hot_sale = Column(Boolean, default=False, nullable=False)
    is_best_seller = Column(Boolean, default=False, nullable=False)
    is_top_pick = Column(Boolean, default=False, nullable=False)
    ranking = Column(Integer, default=0, nullable=False)  # lower sorts first

    seo_title = Column(String(255), nullable=True)
    seo_description = Column(Text, nullable=True)

    published = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    brand_ref = relationship("Brand", back_populates="products")
    category_ref = relationship("Category", back_populates="products")
    images = relationship(
        "ProductImage", back_populates="product",
        cascade="all, delete-orphan", order_by="ProductImage.sort_order",
    )
    sizes = relationship(
        "ProductSize", back_populates="product",
        cascade="all, delete-orphan", order_by="ProductSize.sort_order",
    )

    @property
    def brand_name(self) -> str:
        return self.brand_ref.name if self.brand_ref else ""

    @property
    def category_slug(self) -> str:
        return self.category_ref.slug if self.category_ref else ""


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    src = Column(String(500), nullable=False)  # web path, e.g. /static/images/products/xyz.jpg
    alt = Column(String(255), nullable=False, default="")
    sort_order = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)

    product = relationship("Product", back_populates="images")


class ProductSize(Base):
    __tablename__ = "product_sizes"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    size = Column(String(20), nullable=False)
    available = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="sizes")


# ---------------------------------------------------------------------------
# Homepage merchandising
# ---------------------------------------------------------------------------

class HomepageSection(Base):
    """One row per homepage section (hero, new_arrivals, top_picks, ...).
    `key` is a stable machine name the templates/public routes look up by;
    everything else is owner-editable."""
    __tablename__ = "homepage_sections"

    id = Column(Integer, primary_key=True)
    key = Column(String(60), unique=True, nullable=False, index=True)
    label = Column(String(120), nullable=False)  # human-readable name in admin UI
    enabled = Column(Boolean, default=True, nullable=False)
    heading = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    cta_label = Column(String(120), nullable=True)
    cta_url = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    items = relationship(
        "HomepageSectionItem", back_populates="section",
        cascade="all, delete-orphan", order_by="HomepageSectionItem.sort_order",
    )


class HomepageSectionItem(Base):
    __tablename__ = "homepage_section_items"
    __table_args__ = (UniqueConstraint("section_id", "product_id", name="uq_section_product"),)

    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey("homepage_sections.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    section = relationship("HomepageSection", back_populates="items")
    product = relationship("Product")


class HeroSlide(Base):
    """A single hero carousel slide. Always tied to a real product — image,
    brand, name, price, availability and URL are pulled live from the
    linked Product record, never duplicated here."""
    __tablename__ = "hero_slides"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    headline = Column(String(255), nullable=True)
    eyebrow = Column(String(120), nullable=True)
    description = Column(Text, nullable=True)
    cta_label = Column(String(120), nullable=True)
    cta_url = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    product = relationship("Product")


# ---------------------------------------------------------------------------
# Media & settings
# ---------------------------------------------------------------------------

class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)  # web path under /static
    kind = Column(String(40), nullable=False)  # store_image | store_video | hero_poster | homepage_media
    alt = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class BusinessSettings(Base):
    """Single-row table (id is always 1) mirroring the old business.json."""
    __tablename__ = "business_settings"

    id = Column(Integer, primary_key=True, default=1)

    name = Column(String(120), nullable=False, default="")
    legal_name = Column(String(160), nullable=True)
    tagline = Column(String(255), nullable=False, default="")
    description = Column(Text, nullable=False, default="")

    address_line1 = Column(String(255), nullable=False, default="")
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(120), nullable=False, default="")
    state = Column(String(120), nullable=False, default="")
    postal_code = Column(String(20), nullable=True)
    country = Column(String(4), nullable=False, default="IN")

    phone = Column(String(30), nullable=True)
    whatsapp_number = Column(String(30), nullable=True)
    email = Column(String(160), nullable=True)

    opening_hours = Column(Text, nullable=True)  # newline-separated schema.org day ranges

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    google_maps_url = Column(String(500), nullable=True)

    instagram_url = Column(String(500), nullable=True)
    facebook_url = Column(String(500), nullable=True)
    youtube_url = Column(String(500), nullable=True)

    domain = Column(String(255), nullable=False, default="")

    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def opening_hours_list(self):
        return [line.strip() for line in (self.opening_hours or "").splitlines() if line.strip()]
