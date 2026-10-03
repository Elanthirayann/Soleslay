"""
Pydantic data models for Soleslay.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class ProductImage(BaseModel):
    src: str
    alt: str


class ProductSize(BaseModel):
    """A single real size entry for a product. `available` defaults to True
    so that simply listing a size means it's in stock; set it to False for
    a size that exists in the run but is currently out of stock. Never
    invent a size that isn't part of the product's real size run."""
    size: str
    available: bool = True


AvailabilityStatus = Literal["in_stock", "limited", "out_of_stock", "check_availability"]


class Product(BaseModel):
    slug: str = Field(..., description="SEO-friendly URL slug, e.g. 'onitsuka-tiger-mexico-66-black-white'")
    name: str
    brand: str
    category: str  # one of the CATEGORY slugs below
    description: str
    price: Optional[float] = None
    currency: str = "INR"
    sku: Optional[str] = None
    images: List[ProductImage]
    seo_title: str
    seo_description: str
    in_stock: bool = True
    # Optional explicit override for the 4-state availability system
    # (Available / Limited / Out of Stock / Check Availability). Leave unset
    # to fall back to the plain in_stock boolean — this field exists so the
    # future admin panel can set "limited" without any code change, but
    # nothing here fabricates a "Limited" state until real data says so.
    availability_status: Optional[AvailabilityStatus] = None
    is_new: bool = False
    is_featured: bool = False
    # Not yet populated in products.json — real per-size stock isn't tracked
    # yet. Keep empty until real sizes exist; the homepage Size Run section
    # checks this and stays inactive rather than fabricating availability.
    sizes: List[ProductSize] = []
    # Not yet populated in products.json — added so the data model is ready
    # for real Men/Women navigation once each product is tagged. Values:
    # "men" | "women" | "unisex" | None (untagged). Do not infer this from
    # product name/brand; only set it from real catalog data.
    gender: Optional[str] = None

    colorway: Optional[str] = None
    color_swatches: Optional[List[str]] = None
    silhouette: Optional[str] = None
    materials: Optional[str] = None

    @property
    def primary_image(self) -> ProductImage:
        return self.images[0]

    @property
    def secondary_image(self) -> Optional[ProductImage]:
        """Second real product photo, for the card hover-swap. None (not a
        placeholder) when only one photo exists for this product."""
        return self.images[1] if len(self.images) > 1 else None

    @property
    def price_display(self) -> Optional[str]:
        if self.price is None:
            return None
        return f"₹{self.price:,.0f}"

    @property
    def availability(self) -> AvailabilityStatus:
        if self.availability_status:
            return self.availability_status
        return "in_stock" if self.in_stock else "check_availability"

    @property
    def availability_label(self) -> str:
        return {
            "in_stock": "Available",
            "limited": "Limited Stock",
            "out_of_stock": "Out of Stock",
            "check_availability": "Check Availability",
        }[self.availability]

    @property
    def has_real_sizes(self) -> bool:
        return len(self.sizes) > 0

    @property
    def available_sizes(self) -> List[ProductSize]:
        return [s for s in self.sizes if s.available]

    @property
    def has_available_sizes(self) -> bool:
        return len(self.available_sizes) > 0

    @property
    def catalog_meta(self) -> dict:
        return CATALOG_COLORWAYS.get(self.slug, {})

    @property
    def effective_colorway(self) -> str:
        if self.colorway:
            return self.colorway
        return self.catalog_meta.get("colorway", "Classic Monochrome / Multi-Tone")

    @property
    def effective_color_swatches(self) -> List[str]:
        if self.color_swatches:
            return self.color_swatches
        return self.catalog_meta.get("swatches", ["#171A1E", "#94A3B8", "#FFFFFF"])

    @property
    def effective_materials(self) -> str:
        if self.materials:
            return self.materials
        return self.catalog_meta.get("materials", "Premium Leather, Breathable Mesh & Rubber Traction Sole")

    @property
    def effective_silhouette(self) -> str:
        if self.silhouette:
            return self.silhouette
        return self.catalog_meta.get("silhouette", self.name)

    @property
    def silhouette_colorways(self) -> List[dict]:
        return self.catalog_meta.get("silhouette_colorways", [])

    @property
    def sizes_json(self) -> str:
        """Compact JSON of [{size, available}, ...] for use in an HTML data
        attribute (e.g. the quick-view panel) without adding a Jinja
        `tojson` filter dependency. Left ungraded through Jinja's normal
        autoescaping when interpolated, so it's safe inside an attribute."""
        import json
        return json.dumps([{"size": s.size, "available": s.available} for s in self.sizes], separators=(",", ":"))

    @property
    def whatsapp_text(self) -> str:
        return self.whatsapp_text_for_size(None)

    def whatsapp_text_for_size(self, size: Optional[str] = None, colorway: Optional[str] = None) -> str:
        color = colorway or self.effective_colorway
        base = f"Hi Soleslay, I am interested in {self.name} ({self.brand})"
        if color:
            base += f" - Colorway: {color}"
        if self.sku:
            base += f" (SKU: {self.sku})"
        if size:
            base += f". I need size {size}"
            base += ". Please confirm availability and price."
        else:
            base += ". Could you tell me the available sizes and confirm if it's in stock?"
        return base

    @property
    def gallery_images(self) -> List[dict]:
        """Returns the full multi-angle set of real product images with editorial angle captions.
        If self.images already has multiple images, returns those.
        Otherwise automatically discovers real companion detail photos
        (-detail-upper, -detail-sole, -detail-heel) from disk."""
        import os
        results = [{
            "src": self.images[0].src,
            "alt": self.images[0].alt,
            "tag": "01 // LATERAL",
            "title": "Lateral Profile View",
        }]
        
        main_src = self.images[0].src
        fname = os.path.basename(main_src)
        name_no_ext, ext = os.path.splitext(fname)
        static_dir = os.path.join(os.path.dirname(__file__), "static", "images", "products")
        
        angle_configs = [
            ("-detail-upper", "02 // CRAFT", "Craftsmanship & Upper"),
            ("-detail-sole", "03 // TREAD", "Outsole Tread & Traction"),
            ("-detail-heel", "04 // HEEL", "Heel Structure & Branding"),
        ]
        
        for suffix, tag, title in angle_configs:
            for test_ext in [ext, ".jpg", ".png", ".webp"]:
                candidate = f"{name_no_ext}{suffix}{test_ext}"
                if os.path.exists(os.path.join(static_dir, candidate)):
                    results.append({
                        "src": f"/static/images/products/{candidate}",
                        "alt": f"{self.name} - {title}",
                        "tag": tag,
                        "title": title,
                    })
                    break
        
        if len(results) == 1 and len(self.images) > 1:
            results = []
            labels = ["01 // LATERAL", "02 // CRAFT", "03 // TREAD", "04 // HEEL"]
            for idx, img in enumerate(self.images):
                tag = labels[idx] if idx < len(labels) else f"0{idx+1} // DETAIL"
                results.append({
                    "src": img.src,
                    "alt": img.alt,
                    "tag": tag,
                    "title": f"Angle 0{idx+1}",
                })
                
        return results

    @property
    def editorial_styling_note(self) -> str:
        """Highsnobiety / GQ style editorial curation note tailored to the category & brand."""
        if self.category == "sneakers":
            return (
                f"Pairs best with relaxed straight-leg selvedge denim, heavyweight 280gsm boxy cotton tees, "
                f"and vintage minimalist chore jackets. The tonal {self.effective_colorway} palette effortlessly "
                f"bridges contemporary streetwear culture and elevated everyday luxury."
            )
        elif self.category == "sports-shoes":
            return (
                f"Engineered for performance crossover: style with technical nylon ripstop cargo shorts, "
                f"merino crew socks, and an oversized weatherproof shell. Built to transition seamlessly "
                f"from high-octane trails to urban city commutes."
            )
        elif self.category in ("sandals", "slippers-flip-flops"):
            return (
                f"Embrace the modern utilitarian aesthetic: pair with cropped relaxed linen trousers, "
                f"textured ribbed socks, and a lightweight camp-collar shirt. An effortless warm-weather "
                f"essential engineered for all-day comfort."
            )
        elif self.category == "boots":
            return (
                f"Heritage workwear styling at its finest: team with dark indigo raw denim with a double cuff, "
                f"heavyweight flannel or waffle-knit thermal, and a waxed canvas jacket. The rugged oiled leather "
                f"gains richer character with every wear."
            )
        else:
            return (
                f"A timeless wardrobe anchor. Curated for the discerning collector who values authentic craftsmanship, "
                f"clean proportions, and versatile styling versatility across seasons."
            )

    @property
    def editorial_fit_advice(self) -> str:
        if "jordan" in self.slug or "air-force" in self.slug:
            return "Fits True to Size (TTS). For wide feet, consider going up half a size for extra toe room."
        elif "onitsuka" in self.slug:
            return "Fits True to Size with a slim, streamlined profile. Ideal for narrow to medium-width feet."
        elif "hoka" in self.slug:
            return "True to Size with an accommodating toe box and plush CMEVA cushioning."
        elif "woodland" in self.slug:
            return "True to Standard Indian/UK Sizing. Sturdy anatomical footbed designed for durable all-day support."
        return "Fits True to Size (TTS). We follow standard UK / India footwear sizing."

    def whatsapp_text_for_sourcing(self, size: Optional[str] = None, colorway: Optional[str] = None) -> str:
        color = colorway or self.effective_colorway
        target_size = size or "my size"
        return (
            f"Hi Soleslay Concierge! I want to request custom deadstock sourcing for:\n"
            f"• Model: {self.name} ({self.brand})\n"
            f"• Colorway: {color}\n"
            f"• Size: {target_size}\n"
            f"Could you check your vault network for pricing and 48-72h sourcing availability?"
        )



CATALOG_COLORWAYS = {
    "air-jordan-1-low-craft-inside-out": {
        "colorway": "White / Phantom / Sail / Neutral Grey / Atmosphere",
        "swatches": ["#ECEBE4", "#E2E8F0", "#94A3B8", "#1E293B"],
        "materials": "Deconstructed Suede, Exposed Foam & Ballistic Canvas",
        "silhouette": "Air Jordan 1 Low",
        "silhouette_colorways": [
            {
                "name": "Inside Out (Craft)",
                "colorway": "Sail / Neutral Grey",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "air-jordan-1-low-craft-inside-out",
                "image": "/static/images/products/air-jordan-1-low-craft-inside-out.jpg",
            },
            {
                "name": "Travis Scott 'Reverse Mocha'",
                "colorway": "Sail / Dark Mocha / University Red",
                "status": "Sourced on Demand (48-72h)",
                "in_store": False,
                "slug": "air-jordan-1-low-travis-scott-reverse-mocha",
                "image": "/static/images/products/air-jordan-1-low-craft-inside-out.jpg",
            },
            {
                "name": "Travis Scott 'Olive'",
                "colorway": "Medium Olive / Black / Sail",
                "status": "Sourced on Demand (48-72h)",
                "in_store": False,
                "slug": None,
                "image": "/static/images/products/air-jordan-1-low-craft-inside-out.jpg",
            },
            {
                "name": "Wolf Grey / Golf",
                "colorway": "Wolf Grey / Photon Dust / White",
                "status": "Sourced on Demand (48-72h)",
                "in_store": False,
                "slug": None,
                "image": "/static/images/products/air-jordan-1-low-craft-inside-out.jpg",
            },
        ],
    },
    "air-jordan-1-low-travis-scott-reverse-mocha": {
        "colorway": "Sail / Dark Mocha / University Red / Ridgerock",
        "swatches": ["#ECEBE4", "#3D2B1F", "#DC2626", "#78350F"],
        "materials": "Premium Oiled Nubuck, Sail Tumbled Leather & Reverse Cream Swoosh",
        "silhouette": "Air Jordan 1 Low",
        "silhouette_colorways": [
            {
                "name": "Travis Scott 'Reverse Mocha'",
                "colorway": "Sail / Dark Mocha",
                "status": "Sourced on Demand (48-72h)",
                "in_store": False,
                "slug": "air-jordan-1-low-travis-scott-reverse-mocha",
                "image": "/static/images/products/air-jordan-1-low-craft-inside-out.jpg",
            },
            {
                "name": "Inside Out (Craft)",
                "colorway": "Sail / Neutral Grey",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "air-jordan-1-low-craft-inside-out",
                "image": "/static/images/products/air-jordan-1-low-craft-inside-out.jpg",
            },
            {
                "name": "Travis Scott 'Olive'",
                "colorway": "Medium Olive / Black / Sail",
                "status": "Sourced on Demand (48-72h)",
                "in_store": False,
                "slug": None,
                "image": "/static/images/products/air-jordan-1-low-craft-inside-out.jpg",
            },
            {
                "name": "Wolf Grey / Golf",
                "colorway": "Wolf Grey / White",
                "status": "Sourced on Demand (48-72h)",
                "in_store": False,
                "slug": None,
                "image": "/static/images/products/air-jordan-1-low-craft-inside-out.jpg",
            },
        ],
    },
    "onitsuka-tiger-mexico-66-beige-navy": {
        "colorway": "Beige / Navy Blue / Cream",
        "swatches": ["#F5EBE1", "#1E3A8A", "#D1D5DB"],
        "materials": "Japanese Suede, Premium Nylon & Vulcanized Rubber",
        "silhouette": "Onitsuka Tiger Mexico 66",
        "silhouette_colorways": [
            {
                "name": "Beige & Navy",
                "colorway": "Beige / Navy Blue",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-beige-navy",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-beige-navy.jpg",
            },
            {
                "name": "Metallic Silver",
                "colorway": "Silver / Black",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-silver",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-silver.jpg",
            },
            {
                "name": "Tai-Chi Yellow",
                "colorway": "Yellow / Black",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-yellow-black",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-yellow-black.jpg",
            },
            {
                "name": "Black & White",
                "colorway": "Black / White",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-black-white",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-black-white.jpg",
            },
        ],
    },
    "onitsuka-tiger-mexico-66-silver": {
        "colorway": "Metallic Silver / Black / Cream",
        "swatches": ["#D1D5DB", "#111827", "#F8FAFC"],
        "materials": "Metallic Leather Foil, Suede T-Toe & Rubber Outsole",
        "silhouette": "Onitsuka Tiger Mexico 66",
        "silhouette_colorways": [
            {
                "name": "Metallic Silver",
                "colorway": "Silver / Black",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-silver",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-silver.jpg",
            },
            {
                "name": "Beige & Navy",
                "colorway": "Beige / Navy Blue",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-beige-navy",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-beige-navy.jpg",
            },
            {
                "name": "Tai-Chi Yellow",
                "colorway": "Yellow / Black",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-yellow-black",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-yellow-black.jpg",
            },
            {
                "name": "Black & White",
                "colorway": "Black / White",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-black-white",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-black-white.jpg",
            },
        ],
    },
    "onitsuka-tiger-mexico-66-yellow-black": {
        "colorway": "Tai-Chi Yellow / Black",
        "swatches": ["#FBBF24", "#111827", "#F3F4F6"],
        "materials": "Full-Grain Leather, Suede Accents & Heel Flap",
        "silhouette": "Onitsuka Tiger Mexico 66",
        "silhouette_colorways": [
            {
                "name": "Tai-Chi Yellow",
                "colorway": "Yellow / Black",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-yellow-black",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-yellow-black.jpg",
            },
            {
                "name": "Beige & Navy",
                "colorway": "Beige / Navy Blue",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-beige-navy",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-beige-navy.jpg",
            },
            {
                "name": "Metallic Silver",
                "colorway": "Silver / Black",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-silver",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-silver.jpg",
            },
            {
                "name": "Black & White",
                "colorway": "Black / White",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-black-white",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-black-white.jpg",
            },
        ],
    },
    "onitsuka-tiger-mexico-66-black-white": {
        "colorway": "Black / White / Pure Leather",
        "swatches": ["#111827", "#FFFFFF"],
        "materials": "Full-Grain Leather with Ortholite Cushioning",
        "silhouette": "Onitsuka Tiger Mexico 66",
        "silhouette_colorways": [
            {
                "name": "Black & White",
                "colorway": "Black / White",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-black-white",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-black-white.jpg",
            },
            {
                "name": "Beige & Navy",
                "colorway": "Beige / Navy Blue",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-beige-navy",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-beige-navy.jpg",
            },
            {
                "name": "Metallic Silver",
                "colorway": "Silver / Black",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-silver",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-silver.jpg",
            },
            {
                "name": "Tai-Chi Yellow",
                "colorway": "Yellow / Black",
                "status": "In Store (Guduvanchery)",
                "in_store": True,
                "slug": "onitsuka-tiger-mexico-66-yellow-black",
                "image": "/static/images/products/onitsuka-tiger-mexico-66-yellow-black.jpg",
            },
        ],
    },
    "nike-air-force-1-white": {
        "colorway": "Triple White / Pure Platinum",
        "swatches": ["#FFFFFF", "#F1F5F9"],
        "materials": "Full-Grain Crisp Leather & Nike Air-Sole Unit",
        "silhouette": "Air Force 1 '07",
    },
    "converse-chuck-70-hi-black": {
        "colorway": "Black / Egret / Vintage White",
        "swatches": ["#111827", "#F5F5DC", "#FFFFFF"],
        "materials": "Heavyweight 12oz Canvas, Gloss Egret Foxing",
        "silhouette": "Chuck 70 Hi",
    },
    "woodland-sneaker-tan-nubuck": {
        "colorway": "Raw Camel Tan / Forest Earth",
        "swatches": ["#C19A6B", "#3E2723"],
        "materials": "Premium Italian Nubuck Leather & Dotted Rubber Sole",
        "silhouette": "Woodland Nubuck Sneaker",
    },
    "woodland-boot-tan-4195": {
        "colorway": "Rust Camel Tan / Deep Espresso",
        "swatches": ["#B45309", "#451A03"],
        "materials": "Heavy-Duty Oiled Nubuck & All-Terrain Lug Outsole",
        "silhouette": "Woodland Chukka Boot",
    },
    "woodland-sandal-tan-black-adventure": {
        "colorway": "Desert Tan / Shadow Black",
        "swatches": ["#D97706", "#0F172A"],
        "materials": "Tear-Resistant Webbing & Cushioned EVA Footbed",
        "silhouette": "Woodland Adventure Sandal",
    },
    "woodland-leather-trail-shoe-tan": {
        "colorway": "Oiled Camel Tan / Forest Ochre",
        "swatches": ["#B45309", "#78350F"],
        "materials": "Treated Oiled Nubuck & Padded Collar",
        "silhouette": "Woodland Leather Trail",
    },
    "adidas-terrex-trail-runner-teal": {
        "colorway": "Core Black / Pulse Teal / Sonic Grey",
        "swatches": ["#0F172A", "#0D9488", "#64748B"],
        "materials": "GORE-TEX Waterproof Membrane & Continental Grip Rubber",
        "silhouette": "Adidas Terrex Trail",
    },
    "under-armour-runner-black-grey": {
        "colorway": "Jet Black / Metallic Zinc / White",
        "swatches": ["#020617", "#71717A", "#FFFFFF"],
        "materials": "Engineered Breathable Mesh & Charged Cushioning Foam",
        "silhouette": "Under Armour Performance",
    },
    "woodland-comfort-floaters-khaki": {
        "colorway": "Vintage Khaki / Military Olive",
        "swatches": ["#854D0E", "#3F6212"],
        "materials": "Reinforced PU Straps & Contoured Footbed",
        "silhouette": "Woodland Floaters",
    },
    "woodland-utrek-hiking-boot-tan": {
        "colorway": "Rugged Ochre Tan / Gunmetal",
        "swatches": ["#9A3412", "#334155"],
        "materials": "Full-Grain Oiled Leather & Lugged Traction Outsole",
        "silhouette": "Woodland U-TREK",
    },
    "hoka-speedgoat-7-trail-black": {
        "colorway": "Triple Black / Dark Shadow",
        "swatches": ["#09090B", "#27272A"],
        "materials": "Double Jacquard Mesh, CMEVA Midsole & Vibram Megagrip",
        "silhouette": "Hoka Speedgoat 7",
    },
    "woodland-sandal-4809-cml-tan": {
        "colorway": "Camel Tan / Carbon Black",
        "swatches": ["#D97706", "#18181B"],
        "materials": "Nubuck Straps & Dual-Density Rubber Sole",
        "silhouette": "Woodland Sandal 4809",
    },
}


CATEGORIES = {
    "sneakers": "Sneakers",
    "sports-shoes": "Sports Shoes",
    "sandals": "Sandals",
    "slippers-flip-flops": "Slippers & Flip-Flops",
    "boots": "Boots",
    "belts-accessories": "Belts & Accessories",
}

# Short, real editorial intro copy for each category page — written about the
# category itself (not about specific stock levels or claims that vary), so
# it stays true regardless of which individual products are in the catalog
# at any given time. Avoids thin category pages that are just a title + grid.
CATEGORY_DESCRIPTIONS = {
    "sneakers": "Everyday and statement sneakers from Woodland, Nike, Jordan, Onitsuka Tiger, Converse and more — pick up in Guduvanchery or WhatsApp us to check today's stock.",
    "sports-shoes": "Running and trail shoes built for performance, from Adidas, Under Armour, Hoka and Woodland. WhatsApp us your size and we'll confirm what's on the shelf.",
    "sandals": "Rugged sport sandals for everyday wear around Guduvanchery, with grip outsoles and adjustable straps.",
    "slippers-flip-flops": "Casual slip-ons and flip-flops for home and outdoor comfort.",
    "boots": "Leather boots built for durability, from ankle chukkas to trail-ready hiking boots.",
    "belts-accessories": "Leather belts and footwear accessories to round out the pair.",
}


class BusinessInfo(BaseModel):
    name: str
    legal_name: Optional[str] = None
    tagline: str
    description: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: Optional[str] = None
    country: str = "IN"
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    opening_hours: List[str] = []  # schema.org day ranges, e.g. "Mo-Su 10:00-21:30"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_maps_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    youtube_url: Optional[str] = None
    domain: str = "https://www.soleslay.in"