# Data (cold base)

- **sheets/** — Input CSVs: one per site (product list with UPC, name, etc.).
- **extracted/** — Output: per-product title, description, image_url, dimensions. Only **aurora**, **bazic**, **atiko** have good data so far.
- **images/** — Downloaded product images: **aurora**, **bazic** (one image per product_id).

After running the site analyzer and per-site scrapers, new extracted CSVs and images will go here.
