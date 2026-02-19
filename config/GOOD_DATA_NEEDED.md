# Good info we need (per product)

**Goal:** For every product we want **real, usable** data. That means:

| Field        | Required? | Notes |
|-------------|-----------|--------|
| **title**   | Yes       | Product name (unique per product, not site name). |
| **description** | Yes   | Main product description (not empty). |
| **image_url**   | Yes   | Primary image URL (we also save the file under `data/images/<site>/<product_id>.<ext>`). |
| **dimensions**  | Nice-to-have | Weight or L×W×H when the site provides it. |

**“Good” row:** Has at least **title + description + image_url**. Dimensions are optional but desired.

**How we check:** Run `python3 scripts/validate_extracted.py` — it reports per site:
- **Rightful?** Multiple unique titles (real product pages, not same generic data for every row).
- **With title / description / image / dimensions** — counts so you see how many rows have each field.
- **Complete** — rows that have all of title, description, and image_url (the “good info we need”).

Once those numbers match the number of products you care about, you have the real good info we need.
