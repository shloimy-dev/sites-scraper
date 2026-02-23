# Project Status — Visual Overview

## Match Rate by Site

```
  bruder          ██████████████████████████████████████████████████  98%  (71/72)
  lchaim          █████████████████████████████████████████████░░░░░  91%  (335/365)
  microkick       ██████████████████████████████████████░░░░░░░░░░░░  77%  (7/9)
  chazak          █████████████████████████████████░░░░░░░░░░░░░░░░░  67%  (319/471)
  rhode_island    ██████████████████████████████░░░░░░░░░░░░░░░░░░░░  ~60% (running)
  colours_craft   █████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  42%  (36/84)
  playkidiz       █████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  35%  (93/263)
  enday           █████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  26%  (118/445)
  samvix          █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  19%  (24/126)
  metal_earth     █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  19%  (12/61)
  razor           ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  13%  (4/30)
  winning_moves   █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  11%  (7/60)
```

## Products & Images Collected

```
  lchaim          ████████████████████████████████████  335 products  │  331 images
  chazak          ██████████████████████████████████    319 products  │  317 images
  enday           ████████████                         118 products  │  118 images
  playkidiz       ██████████                            93 products  │    2 images
  bruder          ████████                              71 products  │   71 images
  colours_craft   ████                                  36 products  │   36 images
  samvix          ███                                   24 products  │   23 images
  metal_earth     ██                                    12 products  │   12 images
  microkick       █                                      7 products  │    7 images
  winning_moves   █                                      7 products  │    2 images
  razor           █                                      4 products  │    4 images
  rhode_island    ░░░░░░░░░░░░░░░░░░░░  (still running, ~297 images so far)
```

## Site Status Overview

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    16 TOTAL SITES                               │
  │                                                                 │
  │   ┌───────────────────────────────────────────────────┐         │
  │   │         12 SCRAPED SUCCESSFULLY                   │         │
  │   │                                                   │         │
  │   │   ┌─────────────┐  ┌────────────┐  ┌──────────┐  │         │
  │   │   │  SHOPIFY (6) │  │  WOOCOM (2)│  │ OTHER (4)│  │         │
  │   │   │  bruder      │  │  playkidiz │  │ lchaim   │  │         │
  │   │   │  chazak      │  │  samvix    │  │ rhode_is │  │         │
  │   │   │  microkick   │  │            │  │ metal_ea │  │         │
  │   │   │  colours_cr  │  │            │  │ winning  │  │         │
  │   │   │  enday       │  │            │  │          │  │         │
  │   │   │  razor       │  │            │  │          │  │         │
  │   │   └─────────────┘  └────────────┘  └──────────┘  │         │
  │   └───────────────────────────────────────────────────┘         │
  │                                                                 │
  │   ┌───────────────────────────────────────────────────┐         │
  │   │         4 CANNOT SCRAPE                           │         │
  │   │                                                   │         │
  │   │   goplay ·········· Password-locked store         │         │
  │   │   gi_go ··········· Empty website                 │         │
  │   │   moore ··········· Site in maintenance           │         │
  │   │   sands ··········· Wrong URL (casino site)       │         │
  │   └───────────────────────────────────────────────────┘         │
  └─────────────────────────────────────────────────────────────────┘
```

## Scraping Methods Used

```
  Shopify UPC search ·········· bruder, chazak, microkick
  Shopify suggest API ·········· colours_craft, enday
  Shopify name search ·········· razor
  WooCommerce + DOM ·········· playkidiz, samvix
  AJAX API + UPC match ·········· lchaim
  Autocomplete API ·········· metal_earth
  Browser search ·········· rhode_island
  Product page crawl ·········· winning_moves
```

## Totals

```
  ╔═══════════════════════════════════════════╗
  ║  Products scraped:     1,026+             ║
  ║  Images downloaded:    1,200+             ║
  ║  Sites completed:      12 / 16            ║
  ║  Sheet items covered:  2,480              ║
  ║  Blocked items:        150  (4 sites)     ║
  ╚═══════════════════════════════════════════╝
```
