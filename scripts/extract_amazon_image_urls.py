#!/usr/bin/env python3
"""Fill product image URLs from Amazon search/product pages.

This script is intended for existing extracted CSVs such as:
    data/extracted/playkidiz.csv
    data/extracted/puzelworx.csv

Workflow:
1. Search Amazon by UPC first.
2. If needed, search by title variants.
3. Score search results against the CSV title.
4. Open the best candidate product page and extract the primary image URL.
5. Write an updated CSV, preserving the rest of the columns.

By default, the script writes sibling files with a `.amazon.csv` suffix so the
original extracted CSVs stay untouched until you review the results.
"""

import argparse
import csv
import json
import re
import sys
import time
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs
from urllib.parse import quote_plus
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUTS = [
    ROOT / "data" / "extracted" / "playkidiz.csv",
    ROOT / "data" / "extracted" / "puzelworx.csv",
]
AMAZON_BASE = "https://www.amazon.com"
SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

FILLER_WORDS = {
    "amazon",
    "playkidiz",
    "playkidz",
    "puzelworx",
    "puzzleworx",
    "puzzle",
    "puzzles",
    "pc",
    "pcs",
    "piece",
    "pieces",
    "set",
    "toy",
    "toys",
    "for",
    "with",
    "and",
    "the",
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        nargs="+",
        default=[str(path) for path in DEFAULT_INPUTS],
        help="Extracted CSV files to process.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N rows from each CSV (0 = all rows).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay in seconds between product attempts.",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Replace rows that already have an image_url.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input CSV instead of writing <name>.amazon.csv.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Chromium in headed mode for debugging.",
    )
    return parser.parse_args()


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def ensure_columns(fieldnames):
    for name in ("image_url", "product_url"):
        if name not in fieldnames:
            fieldnames.append(name)
    return fieldnames


def normalize(text):
    text = unescape((text or "").lower())
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def significant_tokens(text):
    tokens = [token for token in normalize(text).split() if token not in FILLER_WORDS]
    return [token for token in tokens if len(token) > 1]


def title_variants(title):
    raw = re.sub(r"\s+", " ", (title or "").strip())
    if not raw:
        return []

    variants = [raw]
    simplified = re.sub(r"\b(playkidiz|playkidz|puzelworx)\b", "", raw, flags=re.I)
    simplified = re.sub(r"\b\d+\s*pc\b", "", simplified, flags=re.I)
    simplified = re.sub(r"\bpuzzle(s)?\b", "", simplified, flags=re.I)
    simplified = re.sub(r"\s+", " ", simplified).strip(" -,:")
    if simplified and simplified.lower() != raw.lower():
        variants.append(simplified)

    unique = []
    seen = set()
    for item in variants:
        key = item.lower()
        if key not in seen and len(item) >= 3:
            seen.add(key)
            unique.append(item)
    return unique


def score_candidate(target_title, candidate_title, query, query_is_upc):
    target_norm = normalize(target_title)
    candidate_norm = normalize(candidate_title)
    if not candidate_norm:
        return -1.0

    score = 0.0
    if candidate_norm == target_norm:
        score += 10.0
    elif target_norm and (candidate_norm in target_norm or target_norm in candidate_norm):
        score += 6.0

    target_tokens = set(significant_tokens(target_title))
    candidate_tokens = set(significant_tokens(candidate_title))
    if target_tokens and candidate_tokens:
        overlap = len(target_tokens & candidate_tokens)
        score += overlap * 1.8
        score += overlap / max(len(target_tokens), 1)

    if query_is_upc:
        score += 2.5
    elif normalize(query) and normalize(query) in candidate_norm:
        score += 1.5

    # Reject clearly weak title searches.
    if not query_is_upc and target_tokens and candidate_tokens:
        overlap = len(target_tokens & candidate_tokens)
        if overlap == 0:
            score -= 10.0

    return score


def amazon_search_url(query):
    return f"{AMAZON_BASE}/s?k={quote_plus(query)}"


def prepare_browser_context(browser):
    context = browser.new_context(
        locale="en-US",
        timezone_id="America/New_York",
        viewport={"width": 1440, "height": 1400},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    )
    context.set_extra_http_headers(
        {
            "accept-language": "en-US,en;q=0.9",
        }
    )
    return context


def maybe_accept_amazon_dialogs(page):
    selectors = [
        "#sp-cc-accept",
        "input[name='accept']",
        "text=Accept Cookies",
        "text=Continue shopping",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=1000):
                locator.click(timeout=1000)
                page.wait_for_timeout(1000)
        except Exception:
            pass


def page_looks_blocked(page):
    text = ""
    try:
        text = (page.title() or "") + "\n" + (page.locator("body").inner_text(timeout=2000) or "")
    except Exception:
        return False
    low = text.lower()
    signals = [
        "enter the characters you see below",
        "type the characters you see in this image",
        "sorry, we just need to make sure you're not a robot",
        "robot check",
        "captcha",
    ]
    return any(signal in low for signal in signals)


def collect_search_candidates(page):
    try:
        page.wait_for_selector("[data-component-type='s-search-result']", timeout=12000)
    except PlaywrightTimeoutError:
        return []

    script = """
    () => {
        const out = [];
        const cards = document.querySelectorAll("[data-component-type='s-search-result']");
        for (const card of cards) {
            const link = card.querySelector("h2 a");
            const title = card.querySelector("h2 span");
            const image = card.querySelector("img.s-image");
            if (!link || !title) continue;
            out.push({
                title: title.textContent.trim(),
                url: link.href,
                image_url: image ? image.src : "",
                asin: card.getAttribute("data-asin") || "",
            });
            if (out.length >= 8) break;
        }
        return out;
    }
    """
    try:
        return page.evaluate(script) or []
    except Exception:
        return []


def choose_candidate(row, query, query_is_upc, candidates):
    title = row.get("title", "")
    best = None
    best_score = -999.0
    for candidate in candidates:
        score = score_candidate(title, candidate.get("title", ""), query, query_is_upc)
        if score > best_score:
            best_score = score
            best = dict(candidate)
            best["score"] = score

    if not best:
        return None

    # Numeric UPC searches are usually very precise, so accept the top match.
    if query_is_upc:
        return best

    if best_score >= 2.5:
        return best
    return None


def clean_amazon_image_url(url):
    url = (url or "").strip()
    if not url:
        return ""
    url = url.replace("\\u0026", "&").replace("\\/", "/")
    if url.startswith("//"):
        url = "https:" + url
    return url


def normalize_amazon_product_url(url):
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.netloc:
        return ""
    host = parsed.netloc.lower()
    if "amazon." not in host:
        return ""
    return f"{parsed.scheme or 'https'}://{parsed.netloc}{parsed.path}"


def decode_duckduckgo_redirect(url):
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "duckduckgo.com" not in parsed.netloc:
        return url
    qs = parse_qs(parsed.query)
    target = qs.get("uddg", [""])[0]
    return target or url


def duckduckgo_amazon_candidates(query):
    search_url = "https://duckduckgo.com/html/?q=" + quote_plus(f"site:amazon.com {query}")
    try:
        response = requests.get(search_url, headers=SEARCH_HEADERS, timeout=30)
        response.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    candidates = []
    for item in soup.select(".result"):
        link = item.select_one(".result__title a")
        if not link:
            continue
        target = normalize_amazon_product_url(decode_duckduckgo_redirect(link.get("href", "")))
        if not target:
            continue
        title = link.get_text(" ", strip=True)
        if not title:
            continue
        candidates.append({"title": title, "url": target, "image_url": "", "asin": ""})
        if len(candidates) >= 6:
            break
    return candidates


def extract_image_from_product_page(page):
    script = r"""
    () => {
        function fromDynamicImage(raw) {
            try {
                const parsed = JSON.parse(raw);
                const urls = Object.keys(parsed || {});
                urls.sort((a, b) => {
                    const av = parsed[a] || [0, 0];
                    const bv = parsed[b] || [0, 0];
                    return (bv[0] * bv[1]) - (av[0] * av[1]);
                });
                return urls[0] || "";
            } catch (err) {
                return "";
            }
        }

        const selectors = [
            "#landingImage",
            "#imgTagWrapperId img",
            "#main-image",
            "img[data-old-hires]",
            "img#ebooksImgBlkFront",
        ];

        for (const selector of selectors) {
            const img = document.querySelector(selector);
            if (!img) continue;
            const oldHires = img.getAttribute("data-old-hires");
            if (oldHires) return oldHires;
            const dynamicImage = img.getAttribute("data-a-dynamic-image");
            if (dynamicImage) {
                const best = fromDynamicImage(dynamicImage);
                if (best) return best;
            }
            const src = img.currentSrc || img.src || "";
            if (src) return src;
        }

        const meta = document.querySelector("meta[property='og:image'], meta[name='og:image']");
        if (meta && meta.content) return meta.content;

        const html = document.documentElement.outerHTML;
        const patterns = [
            /"hiRes":"(https:[^"]+)"/,
            /"large":"(https:[^"]+)"/,
            /"mainUrl":"(https:[^"]+)"/
        ];
        for (const pattern of patterns) {
            const match = html.match(pattern);
            if (match) return match[1];
        }
        return "";
    }
    """
    try:
        image_url = page.evaluate(script) or ""
    except Exception:
        image_url = ""
    return clean_amazon_image_url(image_url)


def try_candidate_product_page(page, chosen):
    page.goto(chosen["url"], wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)
    maybe_accept_amazon_dialogs(page)

    if page_looks_blocked(page):
        raise RuntimeError("Amazon blocked the browser session with a robot check.")

    image_url = extract_image_from_product_page(page) or chosen.get("image_url", "")
    image_url = clean_amazon_image_url(image_url)
    if not image_url:
        return None

    return {
        "image_url": image_url,
        "product_url": page.url,
        "matched_title": chosen.get("title", ""),
        "score": chosen.get("score", 0.0),
    }


def search_and_extract(page, row):
    upc = (row.get("upc") or "").strip()
    title = (row.get("title") or "").strip()
    queries = []
    if upc:
        queries.append((upc, True))
    for variant in title_variants(title):
        queries.append((variant, False))

    seen_queries = set()
    for query, query_is_upc in queries:
        key = (query.lower(), query_is_upc)
        if key in seen_queries:
            continue
        seen_queries.add(key)

        page.goto(amazon_search_url(query), wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        maybe_accept_amazon_dialogs(page)

        if page_looks_blocked(page):
            raise RuntimeError("Amazon blocked the browser session with a robot check.")

        candidates = collect_search_candidates(page)
        chosen = choose_candidate(row, query, query_is_upc, candidates)
        if not chosen:
            continue

        extracted = try_candidate_product_page(page, chosen)
        if extracted:
            extracted["query"] = query
            extracted["query_is_upc"] = query_is_upc
            extracted["source"] = "amazon_search"
            return extracted

    # Fallback: use a web search constrained to amazon.com, then still extract the
    # image from the Amazon product page itself.
    for query, query_is_upc in queries:
        external_candidates = duckduckgo_amazon_candidates(query)
        chosen = choose_candidate(row, query, query_is_upc, external_candidates)
        if not chosen:
            continue
        extracted = try_candidate_product_page(page, chosen)
        if extracted:
            extracted["query"] = query
            extracted["query_is_upc"] = query_is_upc
            extracted["source"] = "duckduckgo_site_search"
            return extracted

    return None


def output_path_for(input_path, in_place):
    if in_place:
        return input_path
    return input_path.with_name(f"{input_path.stem}.amazon{input_path.suffix}")


def process_file(page, input_path, args):
    rows, fieldnames = read_csv(input_path)
    fieldnames = ensure_columns(fieldnames)
    output_path = output_path_for(input_path, args.in_place)

    total = len(rows) if args.limit <= 0 else min(len(rows), args.limit)
    updated = 0
    skipped = 0
    failed = 0

    for index, row in enumerate(rows[:total], start=1):
        existing_image = (row.get("image_url") or "").strip()
        if existing_image and not args.overwrite_existing:
            skipped += 1
            print(f"[{input_path.name}] [{index}/{total}] SKIP existing image")
            continue

        try:
            result = search_and_extract(page, row)
            if result:
                row["image_url"] = result["image_url"]
                row["product_url"] = result["product_url"]
                updated += 1
                print(
                    f"[{input_path.name}] [{index}/{total}] OK "
                    f"source={result['source']} "
                    f"query={result['query']!r} "
                    f"score={result['score']:.2f} "
                    f"title={result['matched_title'][:80]}"
                )
            else:
                failed += 1
                print(
                    f"[{input_path.name}] [{index}/{total}] MISS "
                    f"upc={(row.get('upc') or '').strip()} "
                    f"title={(row.get('title') or '').strip()[:80]}"
                )
        except Exception as exc:
            failed += 1
            print(
                f"[{input_path.name}] [{index}/{total}] ERROR "
                f"upc={(row.get('upc') or '').strip()} error={exc}"
            )

        write_csv(output_path, rows, fieldnames)
        time.sleep(max(args.delay, 0))

    if total < len(rows):
        write_csv(output_path, rows, fieldnames)

    print(
        f"\n{input_path.name}: total={total} updated={updated} skipped={skipped} "
        f"failed={failed} output={output_path}"
    )
    return {"total": total, "updated": updated, "skipped": skipped, "failed": failed}


def main():
    args = parse_args()
    input_paths = [Path(item).resolve() for item in args.input]

    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(f"Input CSV not found: {path}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        context = prepare_browser_context(browser)
        page = context.new_page()
        page.set_default_timeout(45000)

        grand_total = 0
        grand_updated = 0
        grand_skipped = 0
        grand_failed = 0

        try:
            page.goto(AMAZON_BASE, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            maybe_accept_amazon_dialogs(page)

            for path in input_paths:
                stats = process_file(page, path, args)
                grand_total += stats["total"]
                grand_updated += stats["updated"]
                grand_skipped += stats["skipped"]
                grand_failed += stats["failed"]
        finally:
            context.close()
            browser.close()

    print(
        f"\nDONE total={grand_total} updated={grand_updated} "
        f"skipped={grand_skipped} failed={grand_failed}"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
