#!/usr/bin/env python3
"""
Run all site scrapers. Use --limit N to cap rows per scraper.
Skips sites without sheets. Runs sequentially to avoid rate limits.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "sites.yaml"
SITES_DIR = ROOT / "scripts" / "sites"
SHEETS_DIR = ROOT / "data" / "sheets"

# site_id -> scraper script name
SITE_TO_SCRAPER = {
    "atiko": "scrape_akito",
    "audster": "scrape_audster_biz",
    "aurora": "scrape_aurora",
    "bazic": "scrape_bazic",
    "bruder": "scrape_bruder",
    "bz_kinder": "scrape_bz_kinder",
    "casio": "scrape_casio",
    "cazenove": "scrape_cazenove",
    "chazak": "scrape_chazak",
    "colours_craft": "scrape_colours_craft",
    "crayola": "scrape_crayola",
    "daron": "scrape_daron",
    "enday": "scrape_enday",
    "fisher_price": "scrape_fisher_price",
    "gi_go": "scrape_gi_go",
    "gigo": "scrape_gigo",
    "goplay": "scrape_goplay",
    "kent": "scrape_kent",
    "kinder_blast": "scrape_kinder_blast",
    "kinder_shpiel": "scrape_kinder_shpiel",
    "kindervelt": "scrape_kindervelt",
    "lchaim": "scrape_lchaim",
    "mead": "scrape_mead",
    "melissa": "scrape_melissa",
    "metal_earth": "scrape_metal_earth",
    "microkick": "scrape_microkick",
    "moore": "scrape_moore",
    "new_bounce": "scrape_new_bounce",
    "new_york_doll": "scrape_new_york_doll",
    "perler": "scrape_perler",
    "play_build": "scrape_play_build",
    "play_doh_biz": "scrape_play_doh_biz",
    "playkidiz": "scrape_playkidiz",
    "playmags": "scrape_playmags",
    "puzelworx": "scrape_puzelworx",
    "quercetti": "scrape_quercetti_biz",
    "razor": "scrape_razor",
    "rhode_island": "scrape_rhode_island",
    "rina_dina": "scrape_rina_dina",
    "samvix": "scrape_samvix",
    "sands": "scrape_sands",
    "steiff": "scrape_steiff",
    "step2": "scrape_step2",
    "thinkfun": "scrape_thinkfun",
    "tiny_love": "scrape_tiny_love",
    "vtech": "scrape_vtech",
    "winfun": "scrape_winfun",
    "winning_moves": "scrape_winning_moves",
}


def load_config():
    import yaml
    with open(CONFIG) as f:
        return yaml.safe_load(f)["sites"]


def main():
    config = load_config()
    limit = ""
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = f" --limit {sys.argv[idx + 1]}"

    for site_id, scfg in config.items():
        sheet = scfg.get("sheet", site_id)
        sheet_path = SHEETS_DIR / f"{sheet}.csv"
        if not sheet_path.exists():
            for p in SHEETS_DIR.glob("*.csv"):
                if sheet.lower() in p.stem.lower():
                    sheet_path = p
                    break
        if not sheet_path.exists():
            print(f"  SKIP {site_id}: no sheet")
            continue

        scraper = SITE_TO_SCRAPER.get(site_id)
        if not scraper:
            print(f"  SKIP {site_id}: no scraper")
            continue

        script = SITES_DIR / f"{scraper}.py"
        if not script.exists():
            print(f"  SKIP {site_id}: {scraper}.py not found")
            continue

        print(f"\n--- {site_id} ({scraper}) ---")
        cmd = f"python3 {script}{limit}"
        r = subprocess.run(cmd, shell=True, cwd=ROOT)
        if r.returncode != 0:
            print(f"  FAILED: {site_id}")
        else:
            print(f"  OK: {site_id}")


if __name__ == "__main__":
    main()
