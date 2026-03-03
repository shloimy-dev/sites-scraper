# daron

- **URL:** https://modeltoycars.com
- **Platform:** BigCommerce (NOT Shopify)
- **Homepage title:** Your #1 Source for Diecast Cars (when not blocked)

## Scraper strategy (2025-03)

- **Brand page:** `/brands/Daron.html` — lists all Daron products (search URLs trigger Cloudflare)
- **Product URLs:** `https://modeltoycars.com/product-slug/` (no `/products/` prefix)
- **Matching:** Fuzzy name match against catalog, then click-through to product page
- **Limitation:** Product pages may return Cloudflare when accessed from automated browser; try running from a different network or with longer delays

## Recommended strategy: `direct_p` (score 5)

- Non-generic: 0/3
- Unique titles: 1, images: 0

### Sample results

- **[GENERIC]** UPC `93577675597`
  - Title: Attention Required! | Cloudflare
  - OG Desc: 
  - OG Image: 
  - Final URL: https://modeltoycars.com/?p=93577675597

- **[GENERIC]** UPC `817346027048`
  - Title: Attention Required! | Cloudflare
  - OG Desc: 
  - OG Image: 
  - Final URL: https://modeltoycars.com/?p=817346027048

- **[GENERIC]** UPC `830715007649`
  - Title: Attention Required! | Cloudflare
  - OG Desc: 
  - OG Image: 
  - Final URL: https://modeltoycars.com/?p=830715007649

## All strategies

### direct_p — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 93577675597: Attention Required! | Cloudflare
  - [GEN] 817346027048: Attention Required! | Cloudflare
  - [GEN] 830715007649: Attention Required! | Cloudflare

### search_q_upc — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 93577675597: Attention Required! | Cloudflare
  - [GEN] 817346027048: Attention Required! | Cloudflare
  - [GEN] 830715007649: Attention Required! | Cloudflare

### search_s_upc — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 93577675597: Attention Required! | Cloudflare
  - [GEN] 817346027048: Attention Required! | Cloudflare
  - [GEN] 830715007649: Attention Required! | Cloudflare

### shopify_search — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 93577675597: Attention Required! | Cloudflare
  - [GEN] 817346027048: Attention Required! | Cloudflare
  - [GEN] 830715007649: Attention Required! | Cloudflare

### search_q_name — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 93577675597: Attention Required! | Cloudflare
  - [GEN] 817346027048: Attention Required! | Cloudflare
  - [GEN] 830715007649: Attention Required! | Cloudflare

### search_s_name — score 5
- Non-generic: 0/3
- Unique titles: 1, images: 0
  - [GEN] 93577675597: Attention Required! | Cloudflare
  - [GEN] 817346027048: Attention Required! | Cloudflare
  - [GEN] 830715007649: Attention Required! | Cloudflare
