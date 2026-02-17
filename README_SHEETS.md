# Brand sheets in the repo

The Excel/Google Sheets are **not** stored in the repo by default. They live on Google’s servers. This project gives you two ways to get the data into the codebase.

## 1. Sheet list (in code)

All 21 brand sheet links and IDs are in:

- **[config/sheet_links.yaml](config/sheet_links.yaml)**  
  Each brand has: `id`, `name`, `sheet_id`, and the full `link` to open the sheet in the browser.

So the “list” of sheets is already in the repo; the actual data is not.

## 2. Download sheets as CSV into the repo

You can pull the data into the project as CSV files so everything is local.

### Requirements

- Each Google Sheet must be shared as **“Anyone with the link can view”** (otherwise the download will get a login page instead of CSV).
- Python 3 with `requests` and `PyYAML` (see below).

### Steps

1. **Share each sheet**  
   In Google Sheets: Share → “Anyone with the link” → “Viewer”.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the download script:**
   ```bash
   python scripts/download_sheets.py
   ```

4. **Output**  
   CSVs are written to **`data/sheets/`**, one file per brand, e.g.:

   - `data/sheets/enday.csv`
   - `data/sheets/aurora.csv`
   - … (21 files total)

If a sheet is still private, the script will report that brand as failed and remind you to set sharing to “Anyone with the link can view”.

## Summary

| What you want | Where it is |
|---------------|-------------|
| List of sheet links / IDs in code | [config/sheet_links.yaml](config/sheet_links.yaml) |
| Actual sheet data in the repo | Run `python scripts/download_sheets.py` (after making sheets public); files go to `data/sheets/*.csv` |

You don’t need to manually download each Excel/Sheet; the script uses the public CSV export URLs and saves them under `data/sheets/`.
