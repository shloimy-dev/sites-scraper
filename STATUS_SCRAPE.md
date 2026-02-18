# Status: Where we are / Did we figure out each website?

## Short answer

**No.** Only **one** website has been figured out and given a real scraper adapter. The rest are **not** figured out and **not** tested.

---

## What “figured out” means

For each brand we need to:

1. **Discover** the site: How do product URLs work? Where are description, dimensions, and images in the HTML (or in a sitemap/API)?
2. **Document** it (e.g. in a site spec or in code comments).
3. **Implement** an adapter: `get_product_url(row)` and `parse_product_page(html)` for that site.
4. **Test** the scraper and confirm we get descriptions, dimensions, and images.

---

## Current status by brand

| Brand | Scrape URL in config? | Figured out? | Adapter in code? | Tested? |
|-------|------------------------|--------------|------------------|--------|
| **Chazak** | Yes (chazakkinder.com) | **Yes** | **Yes** – product URL from slug(name), parse description block / gallery / JSON-LD | Partially – scraper run; only 4 descriptions in last output (needs re-check) |
| Enday | Yes (enday.com) | **No** | No – uses generic `/products/{slug}` + generic parser | No |
| Aurora | Yes (auroragift.com) | **No** | No | No |
| Bruder | Yes (brudertoys.com) | **No** | No | No |
| Razor | Yes (razor.com) | **No** | No | No |
| Metal Earth | Yes (metalearth.com) | **No** | No | No |
| Winning Moves | Yes (winning-moves.com) | **No** | No | No |
| Moore | Yes (shop.mooretoys.com) | **No** | No | No |
| Kent | Yes (kent.bike) | **No** | No | No |
| Gi-Go | Yes (gigotoys.com.hk) | **No** | No | No |
| Rhode Island | Yes (rinovelty.com) | **No** | No | No |
| Colours Craft | Yes (colourscrafts.com) | **No** | No | No |
| Microkick | Yes (microkickboard.com) | **No** | No | No |
| Lchaim | Yes (lchaimusa.com) | **No** | No | No |
| Samvix | Yes (samvix.com) | **No** | No | No |
| Sands | No (no website) | N/A | N/A | N/A |
| Bazic, Playkidiz, Goplay, Atiko, Play Dough | No scrape URL in config | **No** | No | No |

---

## What’s actually in the code

- **Chazak:**  
  - Product URL: `base + "/products/" + slug(Name(En))`.  
  - Parse: `div.product-block-list__item--description .rte`, meta description, product images, JSON-LD/table for dimensions.

- **All other brands:**  
  - Use a **generic** rule: product URL = `base + "/products/" + slug(Name(En))`, and a **generic** parser (meta description, og:image, any `img` with “product” or “image” in src).  
  - That will only work where the site happens to use `/products/{slug}` and those meta tags. Most sites will need their own URL pattern and selectors.

---

## What still needs to happen

1. **Figure out each website** (except Chazak): open each site, find how product pages are linked, where description / dimensions / images live, and write a short spec or comment.
2. **Add one adapter per brand** in `scripts/scrape_brands.py` (or a separate module per brand) using that spec.
3. **Test** each brand: run the scraper, spot-check output CSV and images, fix until descriptions, dimensions, and images are correct.

So: we are **not** up to date on all sites. Only Chazak has been figured out and given an adapter; the rest are not figured out and not tested.
