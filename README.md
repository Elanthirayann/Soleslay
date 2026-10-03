# Soleslay — Website

FastAPI + Jinja2 website for Soleslay, a footwear store in Guduvanchery, Chennai.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000

## Before going live

1. Open `app/data/business.json` and replace every `REPLACE_...` placeholder
   with real values: address, phone, WhatsApp number (with country code, no
   `+` or spaces, e.g. `919876543210`), opening hours, Google Maps share
   link, and social URLs.
2. Replace `app/static/images/brand/logo.svg` with the real Soleslay logo,
   and add a real `favicon.ico` to the same folder.
3. Review `app/data/products.json` — prices are only filled in where they
   were visible in the supplied photos; everything else shows "Enquire for
   price" until you add a number.
4. Set `domain` in `business.json` to your real production domain once you
   have one — the sitemap, robots.txt and canonical tags all read from it.
5. Swap the placeholder `og:image` / hero poster if you'd like a different
   social-share image.

---

## Admin / CMS system

The site now has a full admin panel so the Soleslay owner can manage
products, images, categories, brands, homepage sections, the hero
carousel, store media and business settings — without touching code.

### 1. Architecture summary

- **No cloud platform was detected** in this repository (no Dockerfile,
  Procfile, or vercel/render/fly config), so storage was chosen to be safe
  under that uncertainty rather than tied to one provider.
- All content that used to live in `products.json` / `business.json` now
  lives in a real database, accessed through SQLAlchemy ORM models
  (`app/models_db.py`).
- The public site (`app/main.py`, `app/data_store.py`) reads **only** from
  the database, on every request (no in-process caching), so admin edits
  show up immediately — including if you ever run multiple worker
  processes.
- The admin panel (`app/routers/admin_*.py`, `app/templates/admin/`) is a
  separate, session-authenticated area with its own look, not linked from
  the public nav.
- `products.json` / `business.json` are left on disk untouched as a
  backup; they are no longer read by the running app after migration.

### 2. Database schema

| Table | Purpose |
|---|---|
| `admin_users` | Owner login (bcrypt password hash, never plaintext) |
| `admin_sessions` | Server-side sessions; cookie holds only an opaque token |
| `login_attempts` | Backs login rate-limiting (pruned automatically) |
| `brands` | name, slug, description, image, active, SEO fields |
| `categories` | name, slug, gender, description, image, SEO fields, active, sort order |
| `products` | all product fields incl. merchandising flags, SEO, `published` |
| `product_images` | multiple images per product, ordering, primary flag, alt text |
| `product_sizes` | real size run per product, availability per size |
| `homepage_sections` | one row per homepage section (key, enabled, heading, description, CTA) |
| `homepage_section_items` | which products are in a section, and in what order |
| `hero_slides` | hero carousel slides, each tied to a real product |
| `media_assets` | store photos/video/hero poster/homepage media |
| `business_settings` | single-row table mirroring the old `business.json` |

Default storage is a SQLite file at `app/data/soleslay.db`. **This only
persists correctly if your hosting platform gives the app a persistent
disk.** If you deploy somewhere with an ephemeral filesystem (most
containers/PaaS without a mounted volume), set the `DATABASE_URL`
environment variable to a managed Postgres instance instead — no code
changes are needed, SQLAlchemy handles both.

### 3. Admin routes

```
/admin/login                          (GET/POST — login)
/admin/logout                         (POST)
/admin                                (dashboard)
/admin/products                       (list, search)
/admin/products/new                   (GET/POST)
/admin/products/{id}/edit             (GET/POST)
/admin/products/{id}/delete           (POST)
/admin/products/{id}/images/upload    (POST, multi-file)
/admin/products/{id}/images/{iid}/{alt|primary|move|delete} (POST)
/admin/products/{id}/sizes/{add|... } (POST)
/admin/categories, /admin/categories/new, /{id}/edit, /{id}/delete
/admin/brands,     /admin/brands/new,     /{id}/edit, /{id}/delete
/admin/homepage                       (list sections)
/admin/homepage/{key}/edit            (GET/POST — heading/description/CTA/products)
/admin/hero                           (list + add slides)
/admin/hero/{id}/{edit|move|delete}   (POST)
/admin/media                          (list/upload/delete store media)
/admin/settings                       (GET/POST — business info)
```

All of the above (except `/admin/login`) require an authenticated session
and reject unauthenticated requests with a redirect to `/admin/login`.
`/admin/` is disallowed in `robots.txt` and not linked from public nav.

### 4. Public routes

Unchanged from before, now backed by the database instead of JSON:
`/`, `/products`, `/products/{slug}`, `/category/{slug}`, `/new-arrivals`,
`/search`, `/about`, `/contact`, `/sitemap.xml`, `/robots.txt`. Draft
(`published=False`) products never appear in listings, the sitemap, or
structured data, and return a real 404 if visited directly.

### 5. Authentication approach

- Passwords hashed with **bcrypt** (never stored or logged in plaintext).
- Sessions are **server-side** (`admin_sessions` table) — the cookie holds
  only a random opaque token, so logout immediately invalidates it
  everywhere, and no session data lives client-side.
- **CSRF tokens** are per-session and required on every state-changing
  form (verified with constant-time comparison).
- **Login rate-limiting**: 5 failed attempts per IP locks that IP out for
  15 minutes (in-memory + DB-logged). Note: this is process-local — if you
  ever run multiple app instances/workers behind a load balancer, swap it
  for a shared store (e.g. Redis).
- Cookies are `httponly`, `samesite=lax`, and marked `secure` automatically
  when `FORCE_HTTPS=1` is set (see env vars below).

### 6. Storage approach (images/media)

- Every uploaded image is **re-decoded and re-encoded through Pillow**
  before being written to disk — this strips anything that isn't valid
  pixel data, so a renamed executable or polyglot file cannot survive an
  upload even if its content-type header is spoofed.
- Filenames are always freshly generated (never taken from user input),
  which rules out path traversal.
- Max 5&nbsp;MB per image, max 4000px per side (rejected above that),
  automatically downscaled to a 2000px max side to keep pages fast.
- Store video uploads (MP4/WEBM) are capped at 50&nbsp;MB and type-checked,
  but are not re-encoded (video re-encoding was out of scope) — only
  upload video from a trusted source (yourself).
- Images live under `app/static/images/{products,categories,brands,store}/`
  and are served as static files, same as before.

### 7. Migration instructions

The database is created automatically on first run (`Base.metadata.create_all`
in `main.py`), so a brand-new install works with no extra steps. To bring
in the **existing** `products.json` / `business.json` data:

```bash
python -m app.migrate
# or, to re-import business.json even if settings were already migrated:
python -m app.migrate --force-business
```

This is idempotent — safe to re-run. It matches products/categories/brands
by slug and updates them in place rather than duplicating them. It does
**not** delete `products.json` / `business.json`.

Then create your admin login (do this once, right after migrating):

```bash
python -m app.create_admin --username <yourusername>
# You'll be prompted for a password (hidden input, min 10 characters).
```

Re-running `create_admin` for the same username resets that user's
password — handy if you ever get locked out.

### 8. Environment variables

| Variable | Required? | Purpose |
|---|---|---|
| `DATABASE_URL` | No (defaults to local SQLite) | Set to a Postgres URL (`postgresql://...`) for any deployment without a persistent disk |
| `FORCE_HTTPS` | No (defaults off) | Set to `1` once the site is served over HTTPS, so the admin session cookie is marked `secure` |

No secrets are hardcoded anywhere in source — the admin password is only
ever provided interactively via `create_admin.py` and stored as a bcrypt
hash.

### 9. Files changed / added

**Added:** `app/db.py`, `app/models_db.py`, `app/auth.py`, `app/uploads.py`,
`app/utils.py`, `app/admin_common.py`, `app/migrate.py`, `app/create_admin.py`,
`app/routers/admin_*.py` (8 files), `app/templates/admin/*.html` (15 files),
`app/static/admin/admin.css`, `app/static/admin/admin.js`.

**Rewritten:** `app/data_store.py` (JSON → database), `app/main.py` (wires
in admin routers, per-request business/category context, dynamic homepage
sections/hero).

**Edited:** `app/templates/base.html` (mega-menu macros now receive
per-request context), `app/templates/index.html` (New Arrivals / Featured
/ Top Picks / Sneaker Feature sections now read their heading, description
and CTA from the admin-managed homepage sections; hero carousel now reads
from admin-managed hero slides, falling back to the original
featured/new-arrival logic when none are configured), `app/static/js/main.js`
(hero thumbnail swap now also respects a per-slide CTA override),
`requirements.txt` (added `sqlalchemy`, `bcrypt`, `pillow`,
`psycopg2-binary`).

**Unchanged:** every other public template, all public CSS, `app/seo.py`,
`app/models.py` (still the Pydantic shapes the public templates render).

### 10. Deployment steps

1. `pip install -r requirements.txt`
2. If deploying somewhere with an ephemeral filesystem, provision a small
   Postgres instance and set `DATABASE_URL`. Otherwise, make sure the
   platform mounts a persistent volume that includes `app/data/` (for the
   SQLite file) and `app/static/images/` (for uploads).
3. `python -m app.migrate` (safe to skip on a brand-new install with no
   existing JSON data)
4. `python -m app.create_admin --username <yourusername>`
5. Set `FORCE_HTTPS=1` once served over HTTPS.
6. Start the app as before: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   (or behind your usual process manager / reverse proxy).
7. Log in at `/admin/login` and take it from there — add products, upload
   images, set up homepage sections and the hero carousel, and fill in
   business settings.

**One current limitation worth knowing:** the "Featured" homepage section's
enable/disable toggle is honored as a *fallback switch* — turning it on
with chosen products shows exactly those products; leaving it enabled with
no products chosen falls back to whichever products are flagged
`is_featured`. If you want it hidden entirely regardless of flagged
products, leave it disabled and don't flag anything as Featured.

---

## Admin panel — responsive redesign

The admin panel's layout, navigation and forms were reworked for
usability and mobile use:

- **Collapsible sidebar** — a fixed left-hand nav with icons on desktop;
  below 900px it becomes an off-canvas drawer opened with a hamburger
  button in a slim top bar, closes on backdrop tap, the × button, Escape,
  or picking a nav link.
- **Responsive forms** — the two-column field grid used throughout
  (product/category/brand/settings forms) collapses to a single column
  below 900px, and every button gets a larger touch target on small
  screens.
- **Responsive tables** — every list/table (products, categories, brands,
  homepage sections, hero slides, sizes, homepage product picker) is
  wrapped so it scrolls horizontally on narrow screens instead of
  squeezing columns unreadably.
- **Visual polish** — consistent card styling, refined color tokens,
  focus rings on form fields, hover/active states on buttons, and section
  headers inside cards for clearer scanning.

Files touched: `app/static/admin/admin.css` (full rewrite),
`app/static/admin/admin.js` (added the drawer toggle logic),
`app/templates/admin/base.html` (mobile top bar + drawer markup + nav
icons), and every admin list/form template that has a `<table>` (wrapped
in a `.table-scroll` container). The `<script>` include for `admin.js`
also moved from being duplicated on five separate pages into `base.html`
once, so it now loads exactly once per page.

## Advanced UI layer

On top of the admin/CMS work, the storefront now has a set of "premium
feel" interactions. All of them are vanilla CSS/JS (no new dependency,
no build step) and every one degrades gracefully — a browser that
doesn't support a given feature just gets the plain version, never a
broken page.

- **Native page-morph transitions** — tapping a product card smoothly
  morphs its image into the detail page's hero image instead of a hard
  reload (CSS `@view-transition`, Chrome/Edge/Safari 18+; other browsers
  just navigate normally).
- **Magnetic buttons** (desktop only) — primary CTAs drift slightly
  toward the cursor and spring back on leave.
- **Spring-press taps** — buttons and size chips get a tactile overshoot
  bounce on press.
- **Hero word-stagger reveal** + **subtle scroll parallax** on the hero
  product image.
- **Floating "Trending" badge** that cycles through recent new arrivals.
- **Skeleton shimmer** while product images load.
- **Quick-view panel** — tapping the eye icon on any product card opens a
  slide-up summary (image, price, sizes, Enquire button) without leaving
  the grid.
- **Gallery crossfade** on the product detail page (replacing the old
  hard image swap).
- **Sticky mobile buy bar** — appears once the main Enquire button
  scrolls out of view; the floating WhatsApp button hides itself on that
  page at that width so the two never overlap.

Everything above respects `prefers-reduced-motion` and only activates
pointer-following effects on devices with a mouse (`hover: hover` +
`pointer: fine`), so touch devices never get a stuck "magnetic" offset.

Files touched: `app/static/css/style.css`, `app/static/js/main.js`,
`app/templates/base.html`, `app/templates/index.html`,
`app/templates/product_detail.html`, `app/templates/_product_card.html`,
`app/templates/_editorial_card.html`, `app/models.py` (added a
`sizes_json` property), `app/main.py` (added a `tojson` Jinja filter).


