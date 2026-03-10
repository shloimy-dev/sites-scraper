# Dimensions Progress & Why Others Don't Have

## Progress Summary

| Status | Count | Stores |
|--------|-------|--------|
| **FULL** (100% dims) | 2 | aurora (413), kent (27) |
| **Partial** (some dims) | 19 | melissa (588), step2 (188), new_bounce (40), steiff (37), cazenove (35), samvix (19), puzzleworx (17), kinder_blast (13), winfun (13), playkidiz.amazon (11), playkidiz (8), razor (7), play_build (7), chazak (5), playmags (2), new_york_doll (3), perler (3), audster (1), ner_mitzvah (1) |
| **0 dims** | 28 | atiko, bazic, bruder, bz_kinder, casio, colours_craft, daron, enday, fisher_price, gi_go, gigo, goplay, kinder_shpiel, kindervelt, lchaim, mead, metal_earth, microkick, moore, puzelworx, quercetti, rhode_island, rina_dina, sands, thinkfun, tiny_love, vtech, winning_moves |

**Total with dims:** 440 (aurora) + 27 (kent) + ~1,100 (partial) ≈ **1,567 products**

---

## Why the Others Don't Have Dimensions

### 1. Site blocked (can't reach product pages)

| Store | Reason |
|-------|--------|
| casio | Access Denied |
| goplay | Password-protected |
| metal_earth | 403 Cloudflare |
| moore | Maintenance mode |
| sands | Access Denied |

### 2. No product_url (can't find product page)

| Store | Reason |
|-------|--------|
| daron | Crawl match failed; no product URLs in extracted |
| gi_go | Search/crawl; sheet may use wrong domain (.com.hk) |
| gigo | Crawl; low match rate |
| mead | Search blocked or no match |
| puzelworx | Search by name; products not found |
| rina_dina | Low match rate; only 5 products in extracted |
| vtech | products.json empty; needs Playwright scraper |
| winning_moves | Crawl; no match |
| atiko | Has product_url but 0 dims extracted (see below) |
| bruder | Has product_url but 0 dims on page |
| colours_craft | Has product_url; dims not on page |
| enday | Has product_url; dims not on page |
| microkick | Has product_url; dims not on page |
| thinkfun | Has product_url; no dims on Ravensburger site |

### 3. Dimensions not on site

| Store | Reason |
|-------|--------|
| fisher_price | No dimensions on shop.mattel.com |
| quercetti | Shopify; no dimension metafields in JSON-LD/HTML |
| rhode_island | No dimensions in JSON-LD, specs, or description |
| thinkfun | No dimensions in product schema or HTML |
| tiny_love | No dimensions in JSON-LD, specs, or description |

### 4. Wrong/empty site

| Store | Reason |
|-------|--------|
| bz_kinder | Site returns empty or wrong domain |
| lchaim | No per-product URLs; API returns generic /Shop |

### 5. Has product_url but extractor found nothing

| Store | Products | Reason |
|-------|----------|--------|
| bazic | 382 | Dims sometimes in description (e.g. "7.75\" x 3.2\" x 1\""); extractor runs but 0 extracted |
| bruder | 72 | JSON-LD/HTML patterns didn't match |
| colours_craft | 36 | Partial; many lack dims on page |
| enday | 118 | Dims not on all product pages |
| atiko | 28 | May need different extraction |
| microkick | 7 | Dims not on page |
| quercetti | 34 | No dims on site |
| rhode_island | 487 | No dims on site |
| tiny_love | 34 | No dims on site |
| vtech | 58 | No product_url or blocked |
| winning_moves | 60 | Crawl didn't match |

---

## Quick Reference: What to Try Next

| Fix | Stores |
|-----|--------|
| Playwright (bypass block) | metal_earth, mead |
| Resolve product_url (search/crawl) | daron, gi_go, gigo, puzelworx, vtech, winning_moves |
| Parse from description first | bazic (already does; may need tuning) |
| Site has no dims | fisher_price, quercetti, rhode_island, thinkfun, tiny_love |
| Site down/wrong | bz_kinder, casio, goplay, moore, sands, lchaim |
