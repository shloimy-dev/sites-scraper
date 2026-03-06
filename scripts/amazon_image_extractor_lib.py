#!/usr/bin/env python3
"""Shared helpers for Amazon image extraction scripts."""

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
AMAZON_BASE = "https://www.amazon.com"
SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
COMMON_FILLER_WORDS = {
    "amazon",
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


def build_parser(default_input, description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--input",
        default=str(default_input),
        help="Extracted CSV file to process.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N rows from the CSV (0 = all rows).",
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
        help="Deprecated compatibility flag. Existing rows are updated by default.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip rows that already have an image_url.",
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
    return parser


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


def output_path_for(input_path, in_place):
    if in_place:
        return input_path
    return input_path.with_name(f"{input_path.stem}.amazon{input_path.suffix}")


def normalize(text):
    text = unescape((text or "").lower())
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_spaces(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def significant_tokens(text, filler_words=None):
    filler = set(COMMON_FILLER_WORDS)
    if filler_words:
        filler.update(filler_words)
    tokens = [token for token in normalize(text).split() if token not in filler]
    return [token for token in tokens if len(token) > 1]


def score_candidate(target_title, candidate_title, query, query_is_upc, filler_words=None):
    target_norm = normalize(target_title)
    candidate_norm = normalize(candidate_title)
    if not candidate_norm:
        return -1.0

    score = 0.0
    if candidate_norm == target_norm:
        score += 10.0
    elif target_norm and (candidate_norm in target_norm or target_norm in candidate_norm):
        score += 6.0

    target_tokens = set(significant_tokens(target_title, filler_words))
    candidate_tokens = set(significant_tokens(candidate_title, filler_words))
    if target_tokens and candidate_tokens:
        overlap = len(target_tokens & candidate_tokens)
        score += overlap * 1.8
        score += overlap / max(len(target_tokens), 1)

    if query_is_upc:
        score += 2.5
    elif normalize(query) and normalize(query) in candidate_norm:
        score += 1.5

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
    context.set_extra_http_headers({"accept-language": "en-US,en;q=0.9"})
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


def choose_candidate(
    row,
    query,
    query_is_upc,
    candidates,
    min_title_score,
    filler_words=None,
    accept_upc_without_threshold=True,
):
    title = row.get("title", "")
    best = None
    best_score = -999.0
    for candidate in candidates:
        score = score_candidate(title, candidate.get("title", ""), query, query_is_upc, filler_words)
        if score > best_score:
            best_score = score
            best = dict(candidate)
            best["score"] = score

    if not best:
        return None

    if query_is_upc and accept_upc_without_threshold:
        return best
    if best_score >= min_title_score:
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
    if "amazon." not in parsed.netloc.lower():
        return ""
    return f"{parsed.scheme or 'https'}://{parsed.netloc}{parsed.path}"


def normalize_result_url(url):
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.netloc or parsed.scheme not in ("http", "https"):
        return ""
    path = (parsed.path or "").lower()
    if path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf")):
        return ""
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def decode_duckduckgo_redirect(url):
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "duckduckgo.com" not in parsed.netloc:
        return url
    query = parse_qs(parsed.query)
    return query.get("uddg", [""])[0] or url


def is_unusable_result_url(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    blocked_hosts = (
        "duckduckgo.com",
        "facebook.com",
        "www.facebook.com",
        "instagram.com",
        "www.instagram.com",
        "youtube.com",
        "www.youtube.com",
        "pinterest.com",
        "www.pinterest.com",
        "tiktok.com",
        "www.tiktok.com",
    )
    if host in blocked_hosts:
        return True
    if "/search" in path and "amazon." not in host:
        return True
    return False


def duckduckgo_candidates(query, site_filter=None):
    full_query = f"site:{site_filter} {query}" if site_filter else query
    search_url = "https://duckduckgo.com/html/?q=" + quote_plus(full_query)
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
        raw_target = decode_duckduckgo_redirect(link.get("href", ""))
        target = normalize_amazon_product_url(raw_target) if site_filter else normalize_result_url(raw_target)
        if not target:
            continue
        if is_unusable_result_url(target):
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


def extract_generic_image_from_page(page, title_tokens):
    script = r"""
    ({ titleTokens }) => {
        function clean(url) {
            if (!url) return "";
            return String(url).replaceAll("\\u0026", "&").replaceAll("\\/", "/").trim();
        }

        function scoreUrl(url) {
            const low = (url || "").toLowerCase();
            let score = 0;
            if (!low || low.startsWith("data:")) return -9999;
            if (low.includes("logo")) score -= 10;
            if (low.includes("icon")) score -= 8;
            if (low.includes("sprite")) score -= 8;
            if (low.includes("placeholder")) score -= 8;
            if (low.match(/\.(jpg|jpeg|png|webp)(\?|$)/)) score += 2;
            return score;
        }

        function scoreText(text) {
            const low = (text || "").toLowerCase();
            let score = 0;
            for (const token of titleTokens || []) {
                if (token && low.includes(token)) score += 2;
            }
            return score;
        }

        const metaSelectors = [
            "meta[property='og:image']",
            "meta[name='og:image']",
            "meta[name='twitter:image']",
            "meta[property='twitter:image']",
            "link[rel='image_src']",
        ];
        const metaCandidates = [];
        for (const selector of metaSelectors) {
            const el = document.querySelector(selector);
            if (!el) continue;
            const url = clean(el.content || el.href || "");
            if (url) metaCandidates.push(url);
        }

        for (const url of metaCandidates) {
            if (scoreUrl(url) > -5) return url;
        }

        const ldJsonScripts = Array.from(document.querySelectorAll("script[type='application/ld+json']"));
        for (const scriptEl of ldJsonScripts) {
            try {
                const obj = JSON.parse(scriptEl.textContent || "null");
                const items = Array.isArray(obj) ? obj : [obj];
                for (const item of items) {
                    const graphItems = item && item["@graph"] ? item["@graph"] : [item];
                    for (const graphItem of graphItems) {
                        if (!graphItem || graphItem["@type"] !== "Product") continue;
                        const image = graphItem.image;
                        if (typeof image === "string" && image) return clean(image);
                        if (Array.isArray(image) && image.length) {
                            if (typeof image[0] === "string") return clean(image[0]);
                            if (image[0] && image[0].url) return clean(image[0].url);
                        }
                        if (image && image.url) return clean(image.url);
                    }
                }
            } catch (err) {
            }
        }

        const imageSelectors = [
            "img[itemprop='image']",
            ".product img",
            "[class*='product'] img",
            "[id*='product'] img",
            "main img",
            "article img",
            "img",
        ];
        const seen = new Set();
        const candidates = [];

        for (const selector of imageSelectors) {
            for (const img of document.querySelectorAll(selector)) {
                const url = clean(
                    img.getAttribute("data-old-hires") ||
                    img.currentSrc ||
                    img.src ||
                    img.getAttribute("data-src") ||
                    ""
                );
                if (!url || seen.has(url)) continue;
                seen.add(url);

                const textBlob = [
                    img.alt || "",
                    img.getAttribute("title") || "",
                    img.className || "",
                    img.id || "",
                    url,
                ].join(" ");

                let score = scoreUrl(url);
                score += scoreText(textBlob);

                const w = img.naturalWidth || img.width || 0;
                const h = img.naturalHeight || img.height || 0;
                score += Math.min((w * h) / 50000, 8);
                if (w >= 400 && h >= 400) score += 4;
                if (w < 120 || h < 120) score -= 8;

                candidates.push({ url, score });
            }
        }

        candidates.sort((a, b) => b.score - a.score);
        return candidates.length ? candidates[0].url : "";
    }
    """
    try:
        image_url = page.evaluate(script, {"titleTokens": title_tokens}) or ""
    except Exception:
        image_url = ""
    return clean_amazon_image_url(image_url)


def try_web_result_page(page, chosen, row, filler_words=None):
    page.goto(chosen["url"], wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(2000)

    title_tokens = significant_tokens(row.get("title", ""), filler_words)[:8]
    image_url = extract_generic_image_from_page(page, title_tokens)
    if not image_url:
        return None

    return {
        "image_url": image_url,
        "product_url": page.url,
        "matched_title": chosen.get("title", ""),
        "score": chosen.get("score", 0.0),
    }


def search_and_extract(page, row, query_builder, min_title_score, filler_words=None):
    queries = []
    seen = set()
    for query, query_is_upc in query_builder(row):
        query = normalize_spaces(query)
        if not query:
            continue
        key = (query.lower(), query_is_upc)
        if key in seen:
            continue
        seen.add(key)
        queries.append((query, query_is_upc))

    for query, query_is_upc in queries:
        page.goto(amazon_search_url(query), wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)
        maybe_accept_amazon_dialogs(page)

        if page_looks_blocked(page):
            raise RuntimeError("Amazon blocked the browser session with a robot check.")

        candidates = collect_search_candidates(page)
        chosen = choose_candidate(
            row, query, query_is_upc, candidates, min_title_score, filler_words
        )
        if not chosen:
            continue

        extracted = try_candidate_product_page(page, chosen)
        if extracted:
            extracted["query"] = query
            extracted["query_is_upc"] = query_is_upc
            extracted["source"] = "amazon_search"
            return extracted

    for query, query_is_upc in queries:
        candidates = duckduckgo_candidates(query, site_filter="amazon.com")
        chosen = choose_candidate(
            row, query, query_is_upc, candidates, min_title_score, filler_words
        )
        if not chosen:
            continue

        extracted = try_candidate_product_page(page, chosen)
        if extracted:
            extracted["query"] = query
            extracted["query_is_upc"] = query_is_upc
            extracted["source"] = "duckduckgo_site_search"
            return extracted

    for query, query_is_upc in queries:
        candidates = duckduckgo_candidates(query)
        chosen = choose_candidate(
            row,
            query,
            query_is_upc,
            candidates,
            min_title_score,
            filler_words,
            accept_upc_without_threshold=False,
        )
        if not chosen:
            continue

        extracted = try_web_result_page(page, chosen, row, filler_words)
        if extracted:
            extracted["query"] = query
            extracted["query_is_upc"] = query_is_upc
            extracted["source"] = "web_search"
            return extracted

    return None


def process_file(page, input_path, args, query_builder, min_title_score, filler_words=None):
    rows, fieldnames = read_csv(input_path)
    fieldnames = ensure_columns(fieldnames)
    output_path = output_path_for(input_path, args.in_place)

    total = len(rows) if args.limit <= 0 else min(len(rows), args.limit)
    updated = 0
    skipped = 0
    failed = 0

    for index, row in enumerate(rows[:total], start=1):
        existing_image = (row.get("image_url") or "").strip()
        if existing_image and args.skip_existing:
            skipped += 1
            print(f"[{input_path.name}] [{index}/{total}] SKIP existing image")
            continue

        try:
            result = search_and_extract(page, row, query_builder, min_title_score, filler_words)
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
                    f"title={normalize_spaces(row.get('title', ''))[:80]}"
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


def run_site_extractor(args, query_builder, min_title_score=2.5, filler_words=None):
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        context = prepare_browser_context(browser)
        page = context.new_page()
        page.set_default_timeout(45000)

        try:
            page.goto(AMAZON_BASE, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2500)
            maybe_accept_amazon_dialogs(page)
            stats = process_file(
                page,
                input_path,
                args,
                query_builder=query_builder,
                min_title_score=min_title_score,
                filler_words=filler_words,
            )
        finally:
            context.close()
            browser.close()

    print(
        f"\nDONE total={stats['total']} updated={stats['updated']} "
        f"skipped={stats['skipped']} failed={stats['failed']}"
    )


def main_guard(main_func):
    try:
        main_func()
    except KeyboardInterrupt:
        sys.exit(130)
