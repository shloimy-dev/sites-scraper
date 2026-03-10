# Dimensions — Remaining Stores

*What we can and cannot get.*

---

## Chart: Stores Missing Dims (Excluding product_url)

*Stores where the reason is product_url are excluded — those will be addressed separately.*

### Site blocked (cannot reach pages)

| Store | Issue |
|-------|-------|
| casio | Access Denied |
| goplay | Password-protected |
| metal_earth | 403 Forbidden (Cloudflare) |
| moore | Maintenance mode |
| sands | Access Denied |

### Dimensions not on site

| Store | Reason |
|-------|--------|
| fisher_price | No dimensions on shop.mattel.com |
| quercetti | Shopify; no dimension metafields in JSON-LD/HTML |
| rhode_island | No dimensions in JSON-LD, specs, or description |
| thinkfun | No dimensions in product schema or HTML (Ravensburger) |
| tiny_love | No dimensions in JSON-LD, specs, or description |

### Partial (some products have dims, others don't)

| Store | Dims | Total | Reason |
|-------|------|-------|--------|
| bazic | 0 | 382 | Dimensions not found on product pages |
| cazenove | 35 | 107 | Only some pages have Width/Height/Depth in HTML |
| chazak | 5 | 359 | Many books; dimensions not in JSON-LD/HTML |
| colours_craft | 46 | 58 | Some products lack dimensions on page |
| enday | 9 | 140 | Dimensions not on all product pages |
| kinder_blast | 13 | 209 | Many books/stickers; no dimensions on page |
| melissa | 343 | 898 | Dimensions in accordion; not all have section |
| ner_mitzvah | 1 | 115 | Most products lack dimensions on page |
| new_york_doll | 3 | 167 | Dimensions not on most product pages |
| perler | 3 | 62 | Dimensions not on all product pages |
| playkidiz | 5 | 131 | Dimensions not on all product pages |
| playmags | 2 | 52 | playmags.com returns 403; uses .co.uk |
| razor | 7 | 26 | Only some have Assembled Product Dimensions |
| samvix | 19 | 58 | WooCommerce dimensions only on some products |
| steiff | 37 | 160 | Size in inches only on some products |
| step2 | 188 | 214 | Some lack Assembled Dimensions on page |
| winfun | 13 | 58 | Dimensions not on all product pages |

### Summary

| Reason | Stores |
|--------|--------|
| Site blocked | 5 |
| Dims not on site | 5 |
| Partial coverage | 17 |

---

## Stores where we CAN get dimensions (implemented & run)

| Store | Method | Status |
|-------|--------|--------|
| **cazenove** | `product-details__item` (Width/Height/Depth in inches) | ✅ 35 products |
| **samvix** | WooCommerce `woocommerce-product-attributes-item--dimensions` | ✅ 19 products |
| **razor** | "Assembled Product Dimensions" / "Product Dimensions" in HTML | ✅ 7 products |
| **aurora** | Parse from `body_html` (Shopify product JSON) — "11\" x 9.5\" x 11.5\"" | ✅ 10+ (run in progress) |

---

## Stores where dimensions are NOT on the site

| Store | Reason |
|-------|--------|
| **rhode_island** | No dimensions in JSON-LD, specs, or description |
| **tiny_love** | No dimensions in JSON-LD, specs, or description |
| **thinkfun** (Ravensburger) | No dimensions in product schema or HTML |
| **quercetti** | Shopify store; no dimension metafields |
| **fisher_price** | No dimensions on shop.mattel.com (180×180 was favicon) |

---

## Resolving product_url (script + scrapers)

**`scripts/resolve_product_urls.py`** — For Shopify sites, fetches `products.json` and matches sheet rows (UPC, name) to product URLs. Resolves: chazak, quercetti, melissa, and other Shopify stores.

```bash
python3 scripts/resolve_product_urls.py
```

**Scrapers** — Run scrapers to populate `product_url` when they find matches:
- **mead** — `scrape_mead.py` (search by name/UPC)
- **daron** — `scrape_daron.py` (catalog match by name)
- **gi_go, gigo** — `scrape_gi_go.py` (crawl categories, match by name)
- **puzelworx** — `scrape_puzelworx.py` (search by name)
- **play_doh_biz** — `scrape_play_doh_biz.py` (direct URL or all-products match)
- **rina_dina** — `scrape_rina_dina.py` (search by UPC/name)

**vtech** — products.json returns empty; use `scrape_vtech.py` (Playwright).

---

## Stores with blocking issues

| Store | Issue |
|-------|-------|
| **lchaim** | All `product_url` point to generic `https://lchaimstore.com/Shop` — no per-product URLs |
| **metal_earth** | 403 Forbidden (Cloudflare) on automated requests |
| **bz_kinder, casio, goplay, moore, sands, kinder_shpiel, kindervelt** | Sheet-only; site returns empty or wrong domain |

---

## Changes made

1. **scraper_lib.py**
   - Razor: "Assembled Product Dimensions" and "Product Dimensions" with Unicode inch symbols
   - Cazenove: Width/Height/Depth from `product-details__item`
   - WooCommerce dimensions table (already present)

2. **extract_dims_aurora.py**
   - Fallback: fetch `/products/{handle}.json` and parse `body_html` for dimensions

3. **Ran dimension scripts**
   - cazenove: 35 products
   - samvix: 19 products
   - razor: 7 products
   - aurora: 10+ (full run in progress)

---

## Next steps for remaining stores

1. **Stores without product_url** — Run scrapers to get product URLs, then run dimension scripts.
2. **metal_earth** — Try Playwright (browser) instead of requests to bypass 403.
3. **lchaim** — Scraper needs to find per-product URLs; currently only has generic shop URL.
