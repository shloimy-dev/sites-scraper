# Extracting description, image, and dimensions from saved HTML

We save full product page HTML under `data/html/<site_id>/<upc_or_id>.html`. Each site has a different structure. This doc records where to find **description**, **images**, and **dimensions** (when available) per site.

---

## Cross-site fallbacks (try first)

- **Meta tags:** `og:title`, `og:description`, `og:image` (and `og:image:secure_url`) — many sites set these on product pages.
- **JSON-LD:** `<script type="application/ld+json">` with `@type: "Product"` — name, description, image(s), sometimes weight/dimensions.
- **Meta description:** `<meta name="description" content="...">` — often product blurb.

---

## Per-site notes

### Shopify-based (chazak, aurora, bazic, enday, bruder, metal_earth, etc.)

- **Caveat:** Some saved HTML has `pageType: "index"` and canonical to `/` — i.e. the `?p=<upc>` URL sometimes returns the homepage, not the product page. For those files there is no product-specific data; extraction will get site-level defaults only.
- **When it is a product page:**
  - Look for `<script type="application/ld+json">` with `"@type": "Product"` (name, description, image, potentially weight).
  - Or theme-specific JSON, e.g. `data-json-product` on product cards (aurora) with `name`, `weight`, `barcode`; `media` may be in another structure.
  - `og:title`, `og:description`, `og:image` when set for the product.
- **Dimensions:** Often in variant `weight` (grams); physical dimensions may be in description text or metafields (not always in initial HTML).

### Winning Moves (winning_moves)

- Classic ASP site. Product content in body.
- **Selectors:** `#add_this_productdetail`, product detail area; `<!-- Product Description -->` comments near product blocks; product images in `img` inside product links (e.g. `href="product/....asp"`).
- **Description:** Look for product name/title and description text in the product detail section (structure may use tables or divs with predictable classes).
- **Image:** Main product `img` in the product detail block; relative paths like `images/...`.
- **Dimensions:** If present, likely in table or text (e.g. “Dimensions: …”).

### Rhode Island (rhode_island)

- Custom platform. Some saved pages are **404** (meta description: “The page you are looking for cannot be found”); skip or mark those.
- **Product pages:** Need to sample a known-good product HTML to document structure (product title, description, image, dimensions). Likely in main content area or a Vue/React data payload.

### Lchaim (lchaim)

- Custom platform (non-Shopify). Generic meta description “Lchaim Productions” on sampled file.
- **Product data:** Likely in main content (product name, description, images). Search for product-specific div/section and image URLs (e.g. `cdn-vt-...`).
- **Dimensions:** If shown, likely in text or a spec block.

### Samvix, Goplay, Razor, Atiko, Colours Craft, Microkick, etc.

- Review one product HTML per site and add notes here: where is the main product title, description, first/main image, and dimensions (if any)?

---

## Output format (for extractors)

Suggested per-product output (e.g. CSV or JSON):

- `site_id`, `product_id` (UPC or sheet id)
- `title` (product name)
- `description` (full or main blurb)
- `image_url` (primary image; full URL)
- `image_urls` (all product images when available)
- `dimensions` (free text or structured, e.g. “L x W x H” or “Weight: …”)
- `raw_html_page_type` (e.g. “product” vs “index”/“404”) when detectable

---

## Scripts

- **Extract script:** `scripts/extract_product_data.py` — reads HTML from `data/html/<site_id>/`, applies per-site logic, writes to `data/extracted/` (e.g. one CSV per site or one JSON per product).
