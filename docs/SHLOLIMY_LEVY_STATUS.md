# Shloimy Levy Stores — Completion Status

Per `docs/AGENT_GUIDE_SHLOLIMY_SITES.md`. Last updated: 2025-02-25.

## Summary

| # | Brand | site_id | Sheet | Config | Analyze | Scraper | Full Data | Notes |
|---|-------|---------|-------|--------|---------|---------|-----------|------|
| 1 | NEW YORK DOLL | new_york_doll | ✅ | ✅ | ✅ | ✅ | ✅ 167/251 | 84 not found (discontinued) |
| 2 | CAZENOVE | cazenove | ✅ | ✅ | ✅ | ✅ | ✅ 126/219 | Crawl category pages for .html product links → match by name |
| 3 | Kinder Blast | kinder_blast | ✅ | ✅ | ✅ | ✅ | ✅ 209/209 | Full data |
| 4 | Mead | mead | ❌ | — | — | — | — | No sheet; uses kinderblast.com |
| 5 | Chazak Kinder | chazak_kinder | ❌ | — | — | — | — | No sheet; uses kinderblast.com |
| 6 | Steiff | steiff | ✅ | ✅ | ✅ | ✅ | ✅ 22/160 | Crawl category pages for /en-us/name-123456 product links → match by name |
| 7 | IZZY&DIZZY | izzy_dizzy | ❌ | — | — | — | — | No sheet; uses steiff.com |
| 8–11 | Crayola, Fisher-Price, Point Games, Kinder Shpiel | — | ❌ | — | — | — | — | No sheets; use steiff.com |
| 12 | METAL EARTH | metal_earth | ✅ | ✅ | ✅ | ✅ | ❌ | Cloudflare blocks Playwright; site returns "Just a moment..." |
| 13 | WINNING MOVES | winning_moves | ✅ | ✅ | ✅ | ✅ | ⚠️ 7/60 | Site has ~10 product pages; many items not on site |
| 14 | KENT | kent | ❌ | ✅ | — | — | — | Sheet is private; cannot download |
| 15 | GoPlay | goplay | ✅ | ✅ | ✅ | — | ❌ | Site password-locked; "download images from google" per Brands |

## Completed with Full Data

- **new_york_doll**: 167 products with description, image, product_url
- **kinder_blast**: 209 products with description, image, product_url
- **cazenove**: 126/219 products (crawl category pages for .html links)
- **steiff**: 22/160 products (crawl category pages for /en-us/name-id links)

## Partial / Blocked

- **metal_earth**: Cloudflare blocks automated access (Playwright gets "Just a moment...")
- **winning_moves**: Only ~10 product pages on site; 7/60 matched
- **goplay**: Password-locked; manual image download from Google
- **kent**: Sheet not publicly accessible

## Sites Needing Sheets

Mead, Chazak Kinder, IZZY&DIZZY, Crayola, Fisher-Price, Point Games, Kinder Shpiel — confirm if they share another brand's sheet (kinderblast.com or steiff.com) before implementing.
