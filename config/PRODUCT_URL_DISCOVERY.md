# Product page URL discovery (per website)

**Update:** `config/sites.yaml` is now filled for all 19 sheets. For most sites the URL is built from the product name slug (`{name_slug}`). Where that fails (404s), run `scripts/discover_urls.py --site <site> [--limit N]` to try resolving via site search; use the output CSV’s “Resolved URL” to add a “Product URL” column.

## Why it varies

- **Shopify-style** (e.g. Chazak, Enday): URLs look like `/products/product-name-slug`. The slug is usually a **kebab-case version of the product name**, not the UPC. So we’d need either a “Product URL” column in the sheet or a slug lookup (e.g. search by UPC and scrape the product URL once).
- **Some sites** use UPC or item number in the path; others use only name slugs.
- **Some brands** may be B2B or sold only through retailers, so there may be no public product page to fetch.

## What we know so far

| Sheet / brand   | Site (if known)        | URL pattern / notes |
|-----------------|------------------------|---------------------|
| **chazak**      | chazakkinder.com       | `/products/{slug}` — slug = hyphenated product name (e.g. `boys-bedroom`). Best: add **Product URL** column or build slug from Name(En). |
| **bazic**       | bazicproducts.com      | `/products/{slug}` or `/product/{slug}/` — slug from product name, not UPC. Same as above. |
| **enday**       | enday.com              | `/products/{slug}` (Shopify). Slug from name. |
| **bruder**      | brudertoyshop.com      | `/products/{number}-{name-slug}-bruder` (e.g. `2771-man-tga-fire-engine-...`). Number + name slug. |
| **playkidiz**   | playkidiz.com          | Product URL structure not confirmed (may be B2B). |
| **moore**       | —                      | No clear official product catalog found (sheet protectors, etc.). |
| **samvix, lchaim, microkick, atiko, colours_craft, rhode_island, goplay, gi_go, sands, winning_moves, metal_earth, razor, aurora** | — | Not checked yet. |

## Recommended approach

1. **Where you can get URLs easily:** Add a **Product URL** column to the CSV, fill it (manually or via a one-time script that searches the site by UPC/name and grabs the product link), then in `config/sites.yaml` set:
   ```yaml
   product_url_column: Product URL
   ```
2. **Where the site uses a simple pattern** (e.g. `/products/{upc}`): Use `url_pattern` in `sites.yaml` with `{upc}` or `{number}`.
3. **Where the URL is name-based:** Either add the Product URL column, or we add a small “discovery” step (e.g. search site by UPC, get product URL, save it) and then run the fetcher.

Once a site is in `sites.yaml` with either `product_url_column` or a working `url_pattern`, `scripts/fetch_pages.py` can fetch and save HTML for that site.

**Unverified sites** (samvix, lchaim, microkick, atiko, colours_craft, goplay, gi_go, sands, rhode_island): `base_url` in `sites.yaml` may be a placeholder. If fetch or discover fails, look up the brand’s real site and fix `base_url` (and `url_pattern` if needed).
