#!/usr/bin/env python3
"""Finalize cats.csv: drop redirect entries (no standalone article) and
backfill any blank descriptions from the article's first sentence."""
import csv
import re
import time
import sys
import requests

API = "https://en.wikipedia.org/w/api.php"
S = requests.Session()
S.headers.update({"User-Agent": "longest-cat-finder/1.0 (research script)"})


def get(params):
    params = {**params, "format": "json"}
    for attempt in range(8):
        r = S.get(API, params=params, timeout=30)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 5)) + 2 * attempt
            print(f"  429, sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        r.raise_for_status()
        time.sleep(0.6)
        return r.json()
    raise RuntimeError("API failed")


def page_info(title):
    """Return (is_redirect, intro_first_sentence)."""
    data = get({
        "action": "query", "prop": "extracts|info",
        "explaintext": 1, "exintro": 1, "titles": title,
    })
    page = next(iter(data["query"]["pages"].values()))
    is_redirect = "redirect" in page
    intro = page.get("extract", "").strip()
    # first sentence: up to first period followed by space/end
    m = re.match(r".*?[.!?](?=\s|$)", intro, re.S)
    sentence = (m.group(0) if m else intro).replace("\n", " ").strip()
    return is_redirect, sentence


def main():
    with open("cats.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    kept = []
    for row in rows:
        name = row["name"]
        if int(row["word_count"]) == 0:
            # these were the redirect suspects; confirm and drop
            is_redir, _ = page_info(name)
            if is_redir:
                print(f"  drop redirect: {name}", file=sys.stderr)
                continue
        if not row["description"]:
            _, sentence = page_info(name)
            row["description"] = sentence
            print(f"  desc backfill {name}: {sentence[:60]}", file=sys.stderr)
        kept.append(row)

    kept.sort(key=lambda r: int(r["word_count"]), reverse=True)
    for i, row in enumerate(kept, 1):
        row["rank"] = i

    with open("cats.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "name", "description", "word_count"])
        w.writeheader()
        w.writerows(kept)
    print(f"Final cats.csv: {len(kept)} rows.", file=sys.stderr)


if __name__ == "__main__":
    main()
