#!/usr/bin/env python3
"""Extract Amazon image URLs for products in playkidiz.csv."""

import re
from pathlib import Path

from amazon_image_extractor_lib import ROOT
from amazon_image_extractor_lib import build_parser
from amazon_image_extractor_lib import main_guard
from amazon_image_extractor_lib import normalize_spaces
from amazon_image_extractor_lib import run_site_extractor
from amazon_image_extractor_lib import significant_tokens

DEFAULT_INPUT = ROOT / "data" / "extracted" / "playkidiz.csv"
PLAYKIDIZ_FILLER_WORDS = {"playkidiz", "playkidz", "rainbow", "card", "scratch"}


def strip_brand(text):
    text = normalize_spaces(text)
    text = re.sub(r"\s+[–-]\s+playkidiz\b", "", text, flags=re.I)
    text = re.sub(r"\bplaykidiz\b", "", text, flags=re.I)
    text = re.sub(r"\bplaykidz\b", "", text, flags=re.I)
    return normalize_spaces(text).strip(" -,:")


def build_queries(row):
    upc = normalize_spaces(row.get("upc", ""))
    title = normalize_spaces(row.get("title", ""))
    base_title = strip_brand(title)
    tokens = significant_tokens(base_title, PLAYKIDIZ_FILLER_WORDS)
    short_subject = " ".join(tokens[:6])

    queries = []
    if upc:
        queries.append((upc, True))

    for value in (title, base_title):
        if value:
            queries.append((value, False))

    if base_title:
        queries.append((f"Playkidiz {base_title}", False))
        queries.append((f"Playkidz {base_title}", False))

    if short_subject:
        queries.append((f"Playkidiz {short_subject}", False))
        queries.append((short_subject, False))

    return queries


def main():
    parser = build_parser(DEFAULT_INPUT, __doc__)
    args = parser.parse_args()
    run_site_extractor(
        args,
        query_builder=build_queries,
        min_title_score=2.0,
        filler_words=PLAYKIDIZ_FILLER_WORDS,
    )


if __name__ == "__main__":
    main_guard(main)
