# Data

- **sheets/** — Input CSVs: one per site (product lists with UPC, name, category, etc.)
- **ready/** — Final scraped data for all completed sites. This is the output.
  - `ready/extracted/` — One CSV per site (upc, title, description, image_url, product_url)
  - `ready/images/` — Downloaded product images organized by site
