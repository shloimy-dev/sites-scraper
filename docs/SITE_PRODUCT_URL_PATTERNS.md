# Site Product URL Patterns — Per-Store Reference

*How each store's product URLs work and how to resolve them from UPC/name.*

---

## Overview

| Platform | URL Pattern | Resolve By | Stores |
|----------|-------------|------------|--------|
| **Shopify** | `/products/{handle}` | UPC search → follow link, or products.json API | bruder, melissa, vtech, tiny_love, new_bounce, playkidiz, kinder_blast, microkick, new_york_doll, quercetti, enday, chazak, colours_craft, bazic, perler, goplay |
| **WooCommerce** | `/product/{slug}/` | `/products/` or `/?s=` search → follow link | playmags, razor, samvix, playkidiz |
| **BigCommerce** | `/product-slug/` or `/categories/.../name.html` | Crawl brand/category or search | daron, puzelworx (toys4u) |
| **Hasbro** | `/product/{slug}/{id}` | Browse all-products or search | play_doh_biz |
| **Custom** | Varies | API, crawl, or sheet | lchaim, cazenove, gigo, steiff, rhode_island, step2 |

---

## Per-Store Detail

### atiko (mostlymusic.com)
- **Platform:** Shopify (scraper: scrape_akito.py)
- **Product URL:** `https://mostlymusic.com/products/{handle}`
- **Resolve:** Search `/search?q={model_code}` (S8, L10, etc.) or name → follow first `/products/` link
- **Status:** Scraper exists; product_url populated when match found

### aurora (auroragift.com)
- **Platform:** Shopify
- **Product URL:** `https://auroragift.com/products/{handle}`
- **Resolve:** products.json API — match by image_url or title (extract_dims_aurora). No dedicated scraper; data from sheet/other source.
- **Status:** Dimension script resolves product_url from products.json

### audster (audster.com)
- **Platform:** Shopify
- **Product URL:** `https://audster.com/products/{handle}`
- **Resolve:** Search or products.json
- **Status:** Biz scraper exists; product_url populated

### bazic (bazic.com)
- **Platform:** Shopify
- **Product URL:** `https://www.bazic.com/products/{handle}`
- **Resolve:** products.json API (match by UPC) — in resolve_product_urls
- **Status:** Working

### bruder (brudertoyshop.com)
- **Platform:** Shopify
- **Product URL:** `https://brudertoyshop.com/products/{handle}`
- **Resolve:** Search `/search?type=product&q={upc}` → follow first product link
- **Status:** ✅ Working

### bz_kinder (bzkinder.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** Sheet-only; site returns empty or wrong domain
- **Status:** ❌ Needs investigation

### casio (casio.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** Sheet-only; site structure not analyzed
- **Status:** ❌ Needs investigation

### cazenove (cazenovejudaica.com/us)
- **Platform:** Custom (Magento-style)
- **Product URL:** `https://cazenovejudaica.com/us/{category}/{slug}.html`
- **Resolve:** Crawl category pages → collect product links → match by name
- **Status:** ✅ Working

### chazak (chazakkinder.com)
- **Platform:** Shopify
- **Product URL:** `https://www.chazakkinder.com/products/{handle}`
- **Resolve:** products.json API (match by UPC) — in resolve_product_urls
- **Status:** Working

### colours_craft (colourscrafts.com)
- **Platform:** Shopify
- **Product URL:** `https://colourscrafts.com/products/{handle}`
- **Resolve:** products.json API
- **Status:** Working

### crayola (crayola.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** No sheet
- **Status:** —

### daron (modeltoycars.com)
- **Platform:** BigCommerce
- **Product URL:** `https://modeltoycars.com/{product-slug}/` (no /products/ prefix)
- **Resolve:** Crawl `/brands/Daron.html` → match by name (search blocked by Cloudflare)
- **Status:** ✅ Working

### enday (enday.com)
- **Platform:** Shopify
- **Product URL:** `https://enday.com/products/{handle}`
- **Resolve:** products.json API
- **Status:** Working

### fisher_price (shop.mattel.com)
- **Platform:** Mattel/Hasbro-style
- **Product URL:** Unknown
- **Resolve:** No dimensions on site
- **Status:** Partial

### gi_go (gigotoys.com.hk)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** Sheet-only; site returns empty or wrong domain
- **Status:** ❌ Needs investigation

### gigo (gigotoys.com)
- **Platform:** Custom
- **Product URL:** `https://www.gigotoys.com/products/{id}-en.html`
- **Resolve:** Crawl category pages (C1-1-en.html, C2-2-en.html) → collect `/products/*.html` links → match by name
- **Status:** ✅ Working

### goplay (goplay.shopping)
- **Platform:** Shopify
- **Product URL:** `https://www.goplay.shopping/products/{handle}`
- **Resolve:** Site is password-protected; search returns /password
- **Status:** ❌ Blocked

### kent (kent.bike)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** Sheet-only; scraper uses sheet fallback only
- **Status:** ❌ Needs investigation

### kinder_blast (kinderblast.com)
- **Platform:** Shopify
- **Product URL:** `https://kinderblast.com/products/{handle}`
- **Resolve:** Search `/search?q={name}` → follow first product link
- **Status:** ✅ Working

### kinder_shpiel (steiff.com/en-us)
- **Platform:** Shopify
- **Product URL:** `https://www.steiff.com/en-us/products/{handle}`
- **Resolve:** Search `/search?q={upc}` returns search results; need to follow first product link
- **Status:** ❌ Scraper uses sheet fallback only; search works per docs

### kindervelt (kindervelt.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** Sheet-only; scraper uses sheet fallback only
- **Status:** ❌ Needs investigation

### lchaim (lchaimstore.com)
- **Platform:** Custom (AJAX API)
- **Product URL:** `https://lchaimstore.com/Shop` (generic — all products)
- **Resolve:** `/Shop/searchItems` API returns all products with UPC; match by UPC. **No per-product URL** — API returns data in HTML, not product URLs
- **Status:** ❌ Needs fix: inspect API response for per-product links (e.g. `/Shop/product/{itemid}`)

### marvins_magic (marvinsmagic.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Status:** No scraper

### mead (mead.com)
- **Platform:** Unknown (likely Shopify)
- **Product URL:** `https://www.mead.com/products/{handle}`
- **Resolve:** Search `/search?q={upc}` or name → follow first product link
- **Status:** Scraper exists; product_url populated when match found

### melissa (melissaanddoug.com)
- **Platform:** Shopify
- **Product URL:** `https://www.melissaanddoug.com/products/{handle}`
- **Resolve:** Search `/search?type=product&q={upc}` → follow first product link; products.json API
- **Status:** ✅ Working

### metal_earth (metalearth.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** 403 Forbidden on automated requests
- **Status:** ❌ Blocked

### microkick (microkickboard.com)
- **Platform:** Shopify
- **Product URL:** `https://microkickboard.com/products/{handle}`
- **Resolve:** Search `/search?type=product&q={upc}` → follow first product link
- **Status:** ✅ Working

### moore (mooreoffice.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** Site in maintenance; search returns 404
- **Status:** ❌ Site down

### ner_mitzvah (nermitzvah.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** No sheet; extracted from API
- **Status:** Partial

### new_bounce (newbouncesport.com)
- **Platform:** Shopify
- **Product URL:** `https://newbouncesport.com/products/{handle}`
- **Resolve:** Search `/search?q={upc}` or name → follow first product link
- **Status:** ✅ Working

### new_york_doll (thenewyorkdollcollection.com)
- **Platform:** Shopify
- **Product URL:** `https://www.thenewyorkdollcollection.com/products/{handle}`
- **Resolve:** Search `/search?q={upc}` or name → follow first product link
- **Status:** ✅ Working

### perler (perler.com)
- **Platform:** Shopify
- **Product URL:** `https://perler.com/products/{handle}`
- **Resolve:** products.json API
- **Status:** Working

### play_build (playbuild.com)
- **Platform:** Shopify
- **Product URL:** `https://www.playbuild.com/products/{handle}`
- **Resolve:** Search `/search?q={name}` → follow first product link
- **Status:** ✅ Working

### play_doh_biz (shop.hasbro.com)
- **Platform:** Hasbro
- **Product URL:** `https://shop.hasbro.com/en-us/product/{slug}/{id}`
- **Resolve:** Browse all-products page; search; or direct URL from Number + slug
- **Status:** Scraper exists; product_url when match found

### playkidiz (playkidiz.com)
- **Platform:** WooCommerce
- **Product URL:** `https://playkidiz.com/product/{slug}/`
- **Resolve:** Search `/?s={upc}` or `/?s={name}` → follow first `/product/` link
- **Status:** ✅ Working

### playmags (playmags.co.uk)
- **Platform:** WooCommerce
- **Product URL:** `https://www.playmags.co.uk/product/{slug}/` (use .co.uk not .com — .com returns 403)
- **Resolve:** Search `/?s={upc}` or name → follow first product link
- **Status:** ✅ Working

### puzelworx (toys4u.com)
- **Platform:** BigCommerce
- **Product URL:** `https://toys4u.com/categories/.../name.html`
- **Resolve:** Search `/search.php?section=product&search_query={name}` → follow first `/categories/` link. UPC search returns "Not Found"
- **Status:** ✅ Working

### puzzleworx (toys4u.com)
- **Platform:** Same as puzelworx
- **Product URL:** Same as puzelworx
- **Resolve:** Crawl category for puzzle product URLs
- **Status:** Working

### quercetti (quercettistore.com)
- **Platform:** Shopify
- **Product URL:** `https://www.quercettistore.com/products/{handle}`
- **Resolve:** products.json API; search
- **Status:** Working

### razor (razor.com)
- **Platform:** WordPress/WooCommerce
- **Product URL:** `https://razor.com/product/{slug}/`
- **Resolve:** Search `/?s={name}` (best) or `/?s={upc}` → follow first `/product/` link
- **Status:** ✅ Working

### rhode_island (rinovelty.com)
- **Platform:** Custom
- **Product URL:** `https://www.rinovelty.com/...` (from search result cards)
- **Resolve:** Search `?term={name}` → product cards with href → visit detail page
- **Status:** ✅ Working

### rina_dina (rinadina.com)
- **Platform:** Custom
- **Product URL:** `https://rinadina.com/{slug}/` (root slug, NOT /products/)
- **Resolve:** Search `/search?q=` or `/?s=` → follow links (reject /products/category/ — those are category pages)
- **Status:** Scraper exists; low match rate

### rubiks (spinmasterspecialty.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Status:** No scraper

### samvix (samvix.com)
- **Platform:** WooCommerce
- **Product URL:** `https://www.samvix.com/index.php/products/{slug}` or similar
- **Resolve:** Search `/?s={name}` → follow first `/products/` link
- **Status:** ✅ Working

### sands (sands.com)
- **Platform:** Unknown
- **Product URL:** Unknown
- **Resolve:** Access Denied on search
- **Status:** ❌ Blocked

### steiff (steiff.com/en-us)
- **Platform:** Shopify
- **Product URL:** `https://www.steiff.com/en-us/products/{handle}`
- **Resolve:** Crawl category pages for /products/ links → build catalog → match by name. Search returns search results page, not product
- **Status:** ✅ Working

### step2 (step2.com)
- **Platform:** Shopify
- **Product URL:** `https://www.step2.com/products/{slug}` — from sheet `deep_link` column
- **Resolve:** **Sheet has product URLs** — CSV feed has deep_link column. No search needed.
- **Status:** ✅ Working (URLs from sheet)

### thinkfun (ravensburger.us)
- **Platform:** Shopify
- **Product URL:** `https://www.ravensburger.us/en-US/products/games/thinkfun/{handle}`
- **Resolve:** Crawl category `/en-US/products/games/thinkfun/` → collect product URLs → match by name
- **Status:** ✅ Working

### tiny_love (tinylove.com)
- **Platform:** Shopify
- **Product URL:** `https://tinylove.com/products/{handle}`
- **Resolve:** Search `/search?q={upc}` or name → follow first product link; products.json API
- **Status:** Working

### vtech (vtechkids.com)
- **Platform:** Shopify
- **Product URL:** `https://www.vtechkids.com/products/{handle}`
- **Resolve:** Search `/search?q=` or `/search?type=product&q=` → follow first product link; products.json API
- **Status:** ✅ Working

### winfun (thelittleluxury.com / winfun.com)
- **Platform:** Custom (winfun.com uses /category/product/123/)
- **Product URL:** `https://www.winfun.com/{category}/product/{id}/` or thelittleluxury.com
- **Resolve:** Search winfun.com; follow product links
- **Status:** Biz scraper exists

### winning_moves (winning-moves.com)
- **Platform:** ASP-style
- **Product URL:** `https://www.winning-moves.com/product/{slug}.asp`
- **Resolve:** Crawl category pages for /product/ links → match by name

---

## Summary: What Needs Fixing

| Store | Issue | Fix |
|-------|-------|-----|
| **lchaim** | All product_url = /Shop | Inspect searchItems API response for per-product links |
| **kinder_shpiel** | Sheet fallback only | Add search → follow first product link (like steiff) |
| **kindervelt** | Sheet fallback only | Investigate site; add search/crawl |
| **kent** | Sheet fallback only | Investigate site; add search/crawl |
| **bz_kinder** | Site returns empty | Investigate correct domain |
| **casio** | Not analyzed | Run deep_analyze; add scraper |
| **gi_go** | Wrong domain (gigotoys.com.hk) | Check config; use gigotoys.com |
| **goplay** | Password protected | Site may be B2B; check if public access |
| **moore** | Maintenance mode | Retry when site is up |
| **sands** | Access Denied | Try Playwright/stealth |
| **metal_earth** | 403 Cloudflare | Try Playwright |

---

## Run Scripts

```bash
# Resolve product URLs for Shopify sites (by UPC/name)
python3 scripts/resolve_product_urls.py

# Run all scrapers (use --limit N to cap rows per store)
python3 scripts/run_all_scrapers.py
python3 scripts/run_all_scrapers.py --limit 10

# Run single scraper
python3 scripts/sites/scrape_aurora.py
python3 scripts/sites/scrape_bruder.py --limit 5

# Run all dimension extraction scripts
python3 scripts/dimensions/run_all.py
python3 scripts/dimensions/run_all.py --limit 10
```

## Run Investigation

```bash
# Analyze one site (URL strategies, scores)
python3 scripts/deep_analyze.py <site_id>

# Deep investigation (robots, sitemap, Shopify API, etc.)
python3 scripts/deep_investigate.py <site_id>
```
