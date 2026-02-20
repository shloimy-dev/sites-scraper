# Data

- **sheets/** — Input CSVs: one per site (product list with UPC, name, etc.).
- **extracted/** — Output from scrapers (per-product CSV). New runs write here.
- **images/** — Downloaded product images. New runs write here.
- **ready/** — **Finished sites (do not rerun).** aurora, bazic, atiko extracted CSVs and aurora/bazic images are here. Use this data for downstream; scrapers should skip these sites.
