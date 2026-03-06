#!/usr/bin/env python3
"""Extract Amazon image URLs for products in puzelworx.csv."""

import re

from amazon_image_extractor_lib import ROOT
from amazon_image_extractor_lib import build_parser
from amazon_image_extractor_lib import main_guard
from amazon_image_extractor_lib import normalize_spaces
from amazon_image_extractor_lib import run_site_extractor
from amazon_image_extractor_lib import significant_tokens

DEFAULT_INPUT = ROOT / "data" / "extracted" / "puzelworx.csv"
PUZELWORX_FILLER_WORDS = {"puzelworx", "puzzleworx", "puzzle", "puzzles"}


def clean_title(text):
    text = normalize_spaces(text)
    text = re.sub(r"\bpuzelworx\b", "", text, flags=re.I)
    text = normalize_spaces(text)
    return text.strip(" -,:")


def piece_count(text):
    match = re.search(r"\b(\d{2,4})\s*pc\b", text, flags=re.I)
    return match.group(1) if match else ""


def build_queries(row):
    upc = normalize_spaces(row.get("upc", ""))
    title = normalize_spaces(row.get("title", ""))
    base_title = clean_title(title)
    tokens = significant_tokens(base_title, PUZELWORX_FILLER_WORDS)
    subject = " ".join(tokens[:6])
    count = piece_count(title)
    is_3d = bool(re.search(r"\b3d\b", title, flags=re.I))

    queries = []
    if upc:
        queries.append((upc, True))

    for value in (title, base_title):
        if value:
            queries.append((value, False))

    if subject and count:
        queries.append((f"PuzzleWorx {subject} {count} piece puzzle", False))
        queries.append((f"{subject} {count} piece puzzle", False))

    if subject and is_3d:
        queries.append((f"PuzzleWorx 3D {subject} puzzle", False))
        queries.append((f"3D {subject} puzzle", False))

    if subject:
        queries.append((f"PuzzleWorx {subject}", False))
        queries.append((subject, False))

    return queries


def main():
    parser = build_parser(DEFAULT_INPUT, __doc__)
    args = parser.parse_args()
    run_site_extractor(
        args,
        query_builder=build_queries,
        min_title_score=3.0,
        filler_words=PUZELWORX_FILLER_WORDS,
    )


if __name__ == "__main__":
    main_guard(main)
