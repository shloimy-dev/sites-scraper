#!/usr/bin/env python3
"""
Deep per-site analyzer.

For each site, this script:
  1. Picks 3 diverse sample products from the sheet
  2. Visits the homepage to capture a "baseline" (title, og:image, etc.)
  3. Tries multiple URL strategies to reach real product pages
  4. If a strategy lands on a search/listing page, follows the first product link
  5. Verifies results are product-specific (not generic/homepage data)
  6. Compares across samples to ensure different products get different data
  7. Scores every strategy and picks the best one
  8. Writes detailed findings to docs/sites/<site_id>.md

Usage:
  python scripts/deep_analyze.py              # analyze all non-ready sites
  python scripts/deep_analyze.py bruder       # analyze one site
"""

import csv, json, os, re, sys, time, yaml
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
DOCS_DIR = ROOT / "docs" / "sites"
ANALYSIS_DIR = ROOT / "data" / "analysis"

WAIT_MS = 4000
TIMEOUT_MS = 20000
READY_SITES = {"atiko", "aurora", "bazic"}

URL_STRATEGIES = [
    ("direct_p",       "{base}/?p={upc}"),
    ("search_q_upc",   "{base}/search?q={upc}"),
    ("search_s_upc",   "{base}/?s={upc}"),
    ("shopify_search",  "{base}/search?type=product&q={upc}"),
    ("search_q_name",  "{base}/search?q={name}"),
    ("search_s_name",  "{base}/?s={name}"),
]

PRODUCT_HREF_KEYWORDS = [
    "/products/", "/product/", "/product_info.php",
    "/p/", "/catalog/product/", "/item/", "/dp/",
]

MAIN_CONTENT_SELECTORS = [
    "main", "#MainContent", "#main-content", "#content",
    "[role='main']", ".main-content", ".search-results",
    ".search-result", "#shopify-section-search-template",
    ".collection-products", ".product-list", ".results",
]

NOT_FOUND_SIGNALS = [
    "page not found", "404", "no results", "0 results",
    "nothing found", "no products found", "sorry, we couldn't find",
]

SEARCH_PAGE_SIGNALS = [
    "search:", "results found", "search results", "results for",
    "you searched for", "showing results",
]


# ── helpers ──────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG) as f:
        return yaml.safe_load(f)["sites"]


def load_samples(sheet_path, n=3):
    with open(sheet_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return []

    upc_col = next((c for c in ("UPC Code", "Origin(UPC)", "Lookup Code") if c in rows[0]), None)
    name_col = next((c for c in ("Name(En)", "Item Name") if c in rows[0]), None)
    url_col = "Product URL" if "Product URL" in (rows[0] if rows else {}) else None

    valid = []
    for r in rows:
        upc = (r.get(upc_col) or "").strip() if upc_col else ""
        name = (r.get(name_col) or "").strip() if name_col else ""
        purl = (r.get(url_col) or "").strip() if url_col else ""
        if upc and len(upc) >= 5:
            valid.append({"upc": upc, "name": name, "product_url": purl})

    if len(valid) == 0:
        return []
    if len(valid) <= n:
        return valid
    step = max(1, len(valid) // n)
    return [valid[i * step] for i in range(n)]


def extract_page_data(html):
    data = {
        "title": "", "og_title": "", "og_description": "",
        "og_image": "", "meta_description": "",
        "json_ld_product": None, "h1": "",
    }

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if m:
        data["title"] = re.sub(r"\s+", " ", m.group(1)).strip()

    for prop, key in [("og:title", "og_title"), ("og:description", "og_description"), ("og:image", "og_image")]:
        m = re.search(
            rf'<meta[^>]*property=["\']?{re.escape(prop)}["\']?[^>]*content=["\']([^"\']*)["\']',
            html, re.I,
        )
        if not m:
            m = re.search(
                rf'<meta[^>]*content=["\']([^"\']*)["\']?[^>]*property=["\']?{re.escape(prop)}["\']',
                html, re.I,
            )
        if m:
            data[key] = m.group(1).strip()

    m = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html, re.I,
    )
    if m:
        data["meta_description"] = m.group(1).strip()

    for m2 in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I,
    ):
        try:
            obj = json.loads(m2.group(1))
            if isinstance(obj, dict) and obj.get("@type") == "Product":
                data["json_ld_product"] = obj
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        data["json_ld_product"] = item
                        break
            elif isinstance(obj, dict) and "@graph" in obj:
                for item in obj["@graph"]:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        data["json_ld_product"] = item
                        break
        except Exception:
            pass

    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m:
        data["h1"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()[:200]

    return data


def find_product_links_via_dom(pw_page, base_url):
    """Use Playwright DOM to find product links in the main content area."""
    links = []
    seen = set()

    for selector in MAIN_CONTENT_SELECTORS:
        try:
            container = pw_page.query_selector(selector)
            if not container:
                continue
            anchors = container.query_selector_all("a[href]")
            for a in anchors:
                href = a.get_attribute("href") or ""
                if any(kw in href for kw in PRODUCT_HREF_KEYWORDS):
                    url = href
                    if url.startswith("//"):
                        url = "https:" + url
                    elif url.startswith("/"):
                        url = base_url.rstrip("/") + url
                    canon = url.split("?")[0].split("#")[0]
                    if canon not in seen:
                        seen.add(canon)
                        links.append(url)
            if links:
                return links[:5]
        except Exception:
            continue

    all_anchors = pw_page.query_selector_all("a[href]")
    for a in all_anchors:
        href = a.get_attribute("href") or ""
        if any(kw in href for kw in PRODUCT_HREF_KEYWORDS):
            url = href
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/"):
                url = base_url.rstrip("/") + url
            canon = url.split("?")[0].split("#")[0]
            if canon not in seen:
                seen.add(canon)
                links.append(url)

    return links[:5]


def looks_not_found(html):
    lower = html[:5000].lower()
    return any(sig in lower for sig in NOT_FOUND_SIGNALS)


def looks_like_search_page(page_data):
    title = (page_data.get("title") or "").lower()
    return any(sig in title for sig in SEARCH_PAGE_SIGNALS)


def is_generic(page_data, baseline):
    if not page_data["title"]:
        return True
    pt = page_data["title"].strip().lower()
    bt = baseline["title"].strip().lower()
    if pt == bt:
        return True
    if page_data["json_ld_product"]:
        return False
    if page_data["og_image"] and baseline["og_image"] and page_data["og_image"] == baseline["og_image"]:
        if not page_data["og_description"] or page_data["og_description"] == baseline.get("og_description", ""):
            return True
    return False


def _is_homepage(current_url, base_url):
    cur = current_url.rstrip("/").split("?")[0].split("#")[0]
    base = base_url.rstrip("/").split("?")[0].split("#")[0]
    return cur == base


def uniqueness_check(results):
    titles = [r["title"] for r in results if r.get("title")]
    images = [r["og_image"] for r in results if r.get("og_image")]
    ut = len(set(titles))
    ui = len(set(images))
    return {"total": len(results), "unique_titles": ut, "unique_images": ui}


def score_strategy(sdata):
    sc = 0
    sc += sdata["non_generic"] * 10
    sc += sdata["uniqueness"]["unique_titles"] * 5
    sc += sdata["uniqueness"]["unique_images"] * 3
    sc += sum(1 for r in sdata["results"] if r.get("og_description")) * 2
    sc += sum(1 for r in sdata["results"] if r.get("json_ld_product")) * 8
    return sc


# ── per-site analysis ────────────────────────────────────────────────

def analyze_site(site_id, site_cfg, browser):
    base_url = site_cfg["base_url"]
    sheet_path = SHEETS_DIR / f"{site_cfg['sheet']}.csv"

    print(f"\n{'=' * 60}")
    print(f"  ANALYZING: {site_id} ({base_url})")
    print(f"{'=' * 60}")

    if not sheet_path.exists():
        print(f"  SKIP: no sheet")
        return None

    samples = load_samples(sheet_path)
    if not samples:
        print(f"  SKIP: no valid samples (need UPC >= 5 chars)")
        return None

    print(f"  Samples ({len(samples)}):")
    for s in samples:
        print(f"    UPC={s['upc']}  Name={s['name'][:50]}")

    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(TIMEOUT_MS)

    site_dir = ANALYSIS_DIR / site_id
    site_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "site_id": site_id, "base_url": base_url,
        "samples": samples, "baseline": {}, "strategies": {},
    }

    # ── homepage baseline ──
    print(f"\n  Fetching homepage...")
    home_html = ""
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT_MS)
        home_html = page.content()
        report["baseline"] = extract_page_data(home_html)
        (site_dir / "homepage.html").write_text(home_html, encoding="utf-8")
        print(f"    Title : {report['baseline']['title'][:80]}")
        print(f"    OG Img: {report['baseline']['og_image'][:80] if report['baseline']['og_image'] else '-'}")
    except Exception as e:
        print(f"    ERROR: {e}")
        report["baseline"] = extract_page_data("")

    # ── product URL column ──
    has_purls = any(s["product_url"] for s in samples)
    if has_purls:
        print(f"\n  [product_url_column]  Sheet has Product URL – testing...")
        report["strategies"]["product_url_column"] = _test_strategy_urls(
            page, samples, report["baseline"], base_url, site_dir,
            label="product_url_column",
            url_fn=lambda s: s["product_url"],
        )

    # ── standard strategies ──
    for strat_name, pattern in URL_STRATEGIES:
        print(f"\n  [{strat_name}]")

        def make_url(s, _pat=pattern):
            return _pat.format(
                base=base_url.rstrip("/"),
                upc=s["upc"],
                name=quote_plus(s["name"]) if s["name"] else s["upc"],
            )

        report["strategies"][strat_name] = _test_strategy_urls(
            page, samples, report["baseline"], base_url, site_dir,
            label=strat_name, url_fn=make_url,
        )

    ctx.close()

    # ── scoring ──
    best_name, best_score = None, -1
    for sn, sd in report["strategies"].items():
        sd["score"] = score_strategy(sd)
        if sd["score"] > best_score:
            best_score = sd["score"]
            best_name = sn

    report["best"] = best_name
    report["best_score"] = best_score

    _write_spec(report)

    (site_dir / "analysis.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8",
    )
    return report


def _test_strategy_urls(page, samples, baseline, base_url, site_dir, *, label, url_fn):
    results = []
    for s in samples:
        url = url_fn(s)
        if not url:
            continue
        entry = _fetch_and_evaluate(page, url, s, baseline, base_url, site_dir, label)
        results.append(entry)
        time.sleep(1.5)

    non_gen = sum(1 for r in results if not r.get("generic"))
    uniq = uniqueness_check(results)
    print(f"    => non-generic {non_gen}/{len(results)}, unique titles {uniq['unique_titles']}, images {uniq['unique_images']}")
    return {"results": results, "non_generic": non_gen, "uniqueness": uniq}


def _fetch_and_evaluate(page, url, sample, baseline, base_url, site_dir, label):
    entry = {
        "upc": sample["upc"], "url_tried": url,
        "title": "", "og_title": "", "og_description": "", "og_image": "",
        "json_ld_product": None, "h1": "",
        "generic": True, "followed": False, "followed_url": "",
        "final_url": "", "not_found": False,
    }
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT_MS)
        html = page.content()
        entry["final_url"] = page.url
        data = extract_page_data(html)
        entry.update(data)
        entry["generic"] = is_generic(data, baseline)
        entry["not_found"] = looks_not_found(html)

        (site_dir / f"{label}_{sample['upc']}.html").write_text(html, encoding="utf-8")

        is_search = looks_like_search_page(data)
        landed_on_homepage = _is_homepage(page.url, base_url)
        needs_follow = (
            (entry["generic"] or entry["not_found"] or is_search or not data.get("json_ld_product"))
            and not landed_on_homepage
        )

        if needs_follow:
            prod_links = find_product_links_via_dom(page, base_url)
            if prod_links:
                print(f"    UPC={sample['upc']}: listing/search page → following {prod_links[0][:70]}")
                try:
                    page.goto(prod_links[0], wait_until="domcontentloaded")
                    page.wait_for_timeout(WAIT_MS)
                    phtml = page.content()
                    pdata = extract_page_data(phtml)
                    entry.update(pdata)
                    entry["generic"] = is_generic(pdata, baseline)
                    entry["followed"] = True
                    entry["followed_url"] = prod_links[0]
                    entry["final_url"] = page.url
                    (site_dir / f"{label}_follow_{sample['upc']}.html").write_text(phtml, encoding="utf-8")
                except Exception as e2:
                    print(f"    follow error: {e2}")

        flag = "GENERIC" if entry["generic"] else "OK"
        jsonld = "JSON-LD" if entry.get("json_ld_product") else ""
        print(f"    UPC={sample['upc']}: [{flag}] {jsonld} title='{entry['title'][:55]}'")

    except Exception as e:
        print(f"    UPC={sample['upc']}: ERROR {e}")

    entry["json_ld_product"] = bool(entry.get("json_ld_product"))
    return entry


# ── output ───────────────────────────────────────────────────────────

def _write_spec(report):
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    sid = report["site_id"]
    base = report["base_url"]
    best = report["best"]
    bl = report["baseline"]

    lines = [
        f"# {sid}", "",
        f"- **URL:** {base}",
        f"- **Homepage title:** {bl.get('title', '')}",
        f"- **Homepage og:image:** {bl.get('og_image', '')}",
        "",
    ]

    if best:
        bs = report["strategies"][best]
        lines += [
            f"## Recommended strategy: `{best}` (score {bs['score']})", "",
            f"- Non-generic: {bs['non_generic']}/{len(bs['results'])}",
            f"- Unique titles: {bs['uniqueness']['unique_titles']}, images: {bs['uniqueness']['unique_images']}",
            "",
            "### Sample results", "",
        ]
        for r in bs["results"]:
            tag = "OK" if not r["generic"] else "GENERIC"
            lines.append(f"- **[{tag}]** UPC `{r['upc']}`")
            lines.append(f"  - Title: {r['title'][:120]}")
            lines.append(f"  - OG Desc: {r['og_description'][:120]}")
            lines.append(f"  - OG Image: {r['og_image'][:120]}")
            if r["followed"]:
                lines.append(f"  - Followed: {r['followed_url'][:120]}")
            lines.append(f"  - Final URL: {r['final_url'][:120]}")
            lines.append("")
    else:
        lines += ["## NO working strategy found", ""]

    lines += ["## All strategies", ""]
    for sn, sd in sorted(report["strategies"].items(), key=lambda x: x[1].get("score", 0), reverse=True):
        lines.append(f"### {sn} — score {sd.get('score', 0)}")
        lines.append(f"- Non-generic: {sd['non_generic']}/{len(sd['results'])}")
        lines.append(f"- Unique titles: {sd['uniqueness']['unique_titles']}, images: {sd['uniqueness']['unique_images']}")
        for r in sd["results"]:
            tag = "OK" if not r["generic"] else "GEN"
            lines.append(f"  - [{tag}] {r['upc']}: {r['title'][:60]}")
        lines.append("")

    path = DOCS_DIR / f"{sid}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  => Wrote {path.relative_to(ROOT)}")


# ── main ─────────────────────────────────────────────────────────────

def main():
    cfg = load_config()
    target = sys.argv[1] if len(sys.argv) > 1 else None

    todo = {}
    for sid, scfg in cfg.items():
        if sid in READY_SITES:
            print(f"SKIP {sid} (data/ready/)")
            continue
        if target and sid != target:
            continue
        todo[sid] = scfg

    print(f"\nAnalyzing {len(todo)} site(s): {', '.join(todo.keys())}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        all_results = {}
        for sid, scfg in todo.items():
            try:
                r = analyze_site(sid, scfg, browser)
                if r:
                    all_results[sid] = r
            except Exception as e:
                print(f"\nFATAL {sid}: {e}")
        browser.close()

    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"{'=' * 60}")
    for sid, r in all_results.items():
        b = r["best"] or "NONE"
        sc = r["best_score"]
        sd = r["strategies"].get(b, {})
        ng = sd.get("non_generic", 0)
        tot = len(sd.get("results", []))
        ut = sd.get("uniqueness", {}).get("unique_titles", 0)
        status = "GOOD" if ng >= 2 and ut >= 2 else ("WEAK" if ng >= 1 else "FAIL")
        print(f"  [{status}] {sid:20s}  best={b:22s}  score={sc:3d}  ok={ng}/{tot}  uniq_titles={ut}")


if __name__ == "__main__":
    main()
