#!/usr/bin/env python3
"""Download playkidiz images using Playwright (site returns 202 to direct requests)."""
import csv, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_lib import img_ext

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "ready" / "extracted" / "playkidiz.csv"
IMG_DIR = ROOT / "data" / "ready" / "images" / "playkidiz"


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    existing = set(f.stem for f in IMG_DIR.iterdir() if f.is_file() and f.stat().st_size > 500)

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    missing = [(r["upc"], r["image_url"]) for r in rows
               if r.get("upc") and r.get("image_url") and r["upc"] not in existing]

    if not missing:
        print("All playkidiz images already downloaded")
        return

    print(f"Downloading {len(missing)} playkidiz images via Playwright...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            accept_downloads=True,
        )
        page = ctx.new_page()

        page.goto("https://playkidiz.com/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        downloaded = 0
        failed = 0

        for i, (upc, url) in enumerate(missing):
            ext = img_ext(url)
            dest = IMG_DIR / f"{upc}{ext}"
            try:
                resp = page.evaluate(f"""
                    async () => {{
                        try {{
                            const r = await fetch("{url}");
                            if (!r.ok) return null;
                            const blob = await r.blob();
                            return new Promise((resolve) => {{
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            }});
                        }} catch(e) {{
                            return null;
                        }}
                    }}
                """)
                if resp and resp.startswith("data:"):
                    import base64
                    header, b64 = resp.split(",", 1)
                    data = base64.b64decode(b64)
                    if len(data) > 500:
                        with open(dest, "wb") as f:
                            f.write(data)
                        downloaded += 1
                    else:
                        failed += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1

            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(missing)}] downloaded={downloaded} failed={failed}")
            time.sleep(0.3)

        ctx.close()
        browser.close()

    print(f"\nDone: {downloaded} downloaded, {failed} failed")


if __name__ == "__main__":
    main()
