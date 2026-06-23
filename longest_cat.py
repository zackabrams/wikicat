#!/usr/bin/env python3
"""Find the individual cat with the longest English Wikipedia article by word count."""
import re
import sys
import time
import requests

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "longest-cat-finder/1.0 (research script)"}
S = requests.Session()
S.headers.update(HEADERS)


def get(params):
    params = {**params, "format": "json"}
    for attempt in range(8):
        try:
            r = S.get(API, params=params, timeout=30)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 5)) + 2 * attempt
                print(f"  429, sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            time.sleep(0.5)  # be polite
            return r.json()
        except Exception as e:
            print(f"  retry ({e})", file=sys.stderr)
            time.sleep(3)
    raise RuntimeError("API failed repeatedly")


def category_members(cat, seen_cats=None, depth=0, max_depth=3):
    """Recursively gather article (ns=0) page titles under a category."""
    if seen_cats is None:
        seen_cats = set()
    if cat in seen_cats or depth > max_depth:
        return set()
    seen_cats.add(cat)
    pages = set()
    cont = {}
    while True:
        data = get({
            "action": "query", "list": "categorymembers",
            "cmtitle": cat, "cmlimit": "500",
            "cmtype": "page|subcat", **cont,
        })
        for m in data.get("query", {}).get("categorymembers", []):
            title = m["title"]
            if title.startswith("Category:"):
                pages |= category_members(title, seen_cats, depth + 1, max_depth)
            elif m["ns"] == 0:
                pages.add(title)
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return pages


def word_count(titles):
    """Fetch plain-text extracts and count words, batching titles."""
    counts = {}
    titles = list(titles)
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        cont = {}
        # accumulate extracts (extracts only returns ~20 full at once)
        while True:
            data = get({
                "action": "query", "prop": "extracts",
                "explaintext": 1, "titles": "|".join(batch),
                "exlimit": "max", **cont,
            })
            for p in data.get("query", {}).get("pages", {}).values():
                if "extract" in p:
                    text = p["extract"]
                    counts[p["title"]] = len(re.findall(r"\b\w+\b", text))
            if "continue" in data:
                cont = data["continue"]
            else:
                break
        print(f"  processed {min(i+20, len(titles))}/{len(titles)}", file=sys.stderr)
    return counts


def descriptions(titles):
    """Fetch short (Wikidata) descriptions, batching by 50."""
    descs = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = get({
            "action": "query", "prop": "description",
            "titles": "|".join(batch),
        })
        for p in data.get("query", {}).get("pages", {}).values():
            descs[p["title"]] = p.get("description", "")
    return descs


# Entries in the category that are not individual cats (lists / general topics).
NON_CATS = {"List of individual cats", "Ship's cat"}


def main():
    import csv
    print("Gathering individual cats from Wikipedia categories...", file=sys.stderr)
    titles = category_members("Category:Individual cats")
    titles -= NON_CATS
    print(f"Found {len(titles)} individual-cat articles.", file=sys.stderr)
    counts = word_count(titles)
    print("Fetching short descriptions...", file=sys.stderr)
    descs = descriptions(counts.keys())
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)

    with open("cats.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "name", "description", "word_count"])
        for rank, (title, n) in enumerate(ranked, 1):
            w.writerow([rank, title, descs.get(title, ""), n])
    print(f"Wrote {len(ranked)} rows to cats.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
