#!/usr/bin/env python3
import re
from pathlib import Path

FILES = [
    "scrape_bruder.py", "scrape_crayola.py", "scrape_daron.py", "scrape_enday.py",
    "scrape_gi_go.py", "scrape_gigo.py", "scrape_kinder_blast.py", "scrape_microkick.py",
    "scrape_new_bounce.py", "scrape_new_york_doll.py", "scrape_perler.py", "scrape_puzelworx.py",
    "scrape_razor.py", "scrape_samvix.py", "scrape_winfun.py", "scrape_metal_earth.py",
    "scrape_cazenove.py", "scrape_colours_craft.py", "scrape_goplay.py", "scrape_kindervelt.py",
    "scrape_kinder_shpiel.py", "scrape_kent.py", "scrape_lchaim.py", "scrape_moore.py",
    "scrape_play_build.py", "scrape_sands.py", "scrape_step2.py", "scrape_bz_kinder.py",
    "scrape_casio.py", "scrape_tiny_love.py", "scrape_winning_moves.py", "scrape_thinkfun.py",
    "scrape_vtech.py",
]
BASE = Path("scripts/sites")

def process(path):
    content = path.read_text(encoding="utf-8")
    orig = content
    if "extracted_path = ext_dir" in content:
        return False
    content = re.sub(r"(img_dir\.mkdir\(parents=True,\s*exist_ok=True\))\s*\n", r"\1\n    extracted_path = ext_dir / f"{SITE_ID}.csv"\n", content, count=1)
    if "extracted_path = ext_dir" not in content:
        content = re.sub(r"(ext_dir\.mkdir\(parents=True,\s*exist_ok=True\))\s*\n", r"\1\n    extracted_path = ext_dir / f"{SITE_ID}.csv"\n", content, count=1)
    lines = content.split("\n")
    out = []
    i = 0
    while i < len(lines):
        out.append(lines[i])
        line = lines[i]
        if re.match(r"^\s+results\.append\(", line):
            if line.rstrip().endswith(")"):
                if i+1 < len(lines) and "write_csv(results" not in lines[i+1]:
                    indent = " " * (len(line) - len(line.lstrip()))
                    out.append(indent + "write_csv(results, extracted_path)")
            else:
                j = i + 1
                while j < len(lines):
                    out.append(lines[j])
                    if ")" in lines[j] and lines[j].rstrip().endswith(")"):
                        break
                    j += 1
                i = j
                if i+1 < len(lines) and "write_csv(results" not in lines[i+1]:
                    indent = " " * (len(lines[i]) - len(lines[i].lstrip()))
                    out.append(indent + "write_csv(results, extracted_path)")
        i += 1
    content = "\n".join(out)
    content = re.sub(r'write_csv\(results,\s*ext_dir\s*/\s*f\"\{SITE_ID\}\.csv\"\)', "write_csv(results, extracted_path)", content)
    content = re.sub(r"write_csv\(results,\s*out_path\)", "write_csv(results, extracted_path)", content)
    content = re.sub(r'\s*out_path = ext_dir / f\"\{SITE_ID\}\.csv\"\s*\n', "\n", content)
    content = re.sub(r"out_path\.write_text\(", "extracted_path.write_text(", content)
    if content != orig:
        path.write_text(content, encoding="utf-8")
        return True
    return False

for f in FILES:
    p = BASE / f
    if p.exists():
        if process(p):
            print("Updated:", f)
        else:
            print("No change:", f)
    else:
        print("Missing:", f)
