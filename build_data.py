#!/usr/bin/env python3
"""Build cats_data.json for the HTML page.

Reads cats.csv (name, description, word_count, pageviews_12mo, pct_of_Cat) and
enriches each cat with:
  type       - friendly category derived from its Wikipedia categories
  thumb      - Wikimedia thumbnail URL (or null -> placeholder in the page)
  url        - link to the Wikipedia article
  monthly    - 12 monthly pageview counts (Jun 2025 .. May 2026) for a sparkline
"""
import csv
import json
import time
import sys
import urllib.parse
import requests

API = "https://en.wikipedia.org/w/api.php"
REST = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        "en.wikipedia/all-access/all-agents/{title}/monthly/{start}/{end}")
S = requests.Session()
S.headers.update({"User-Agent": "longest-cat-finder/1.0 (research; zackdabrams@gmail.com)"})

START, END = "2025060100", "2026053100"
MONTHS = [f"2025{m:02d}" for m in range(6, 13)] + [f"2026{m:02d}" for m in range(1, 6)]

# (label, category-substring keywords) in priority order; first match wins.
TYPE_RULES = [
    ("Fictional",          ["fictional cats"]),
    ("Space",              ["animals in space", "in spaceflight"]),
    ("Cloned",             ["cloned cats"]),
    ("Government mouser",  ["chief mousers", "mouser"]),
    ("Presidential",       ["presidential cats"]),
    ("Political",          ["mayors of", "elections", "novelty candidates"]),
    ("Ship's cat",         ["ship's cats"]),
    ("Station cat",        ["railway station cats", "station master"]),
    ("Internet celebrity", ["internet celebrit", "internet meme"]),
    ("Record holder",      ["world record"]),
    ("Science",            ["hoaxes in science", "in science", "research"]),
    ("Working cat",        ["working cats", "military animals", "police"]),
]


def get(params):
    params = {**params, "format": "json"}
    for attempt in range(8):
        r = S.get(API, params=params, timeout=30)
        if r.status_code == 429:
            time.sleep(4 + 2 * attempt); continue
        r.raise_for_status()
        time.sleep(0.4)
        return r.json()
    raise RuntimeError("API failed")


def classify(categories):
    low = [c.lower() for c in categories]
    for label, keys in TYPE_RULES:
        if any(any(k in c for c in low) for k in keys):
            return label
    return "Other"


def fetch_meta(titles):
    """Return {title: (type, thumb_url_or_None)} via batched category+image calls."""
    meta = {}
    for i in range(0, len(titles), 40):
        batch = titles[i:i + 40]
        cats = {t: [] for t in batch}
        cont = {}
        while True:  # categories can paginate
            data = get({
                "action": "query", "prop": "categories|pageimages",
                "cllimit": "max", "clshow": "!hidden",
                "piprop": "thumbnail", "pithumbsize": "200",
                "titles": "|".join(batch), **cont,
            })
            for p in data["query"]["pages"].values():
                t = p["title"]
                cats.setdefault(t, [])
                cats[t] += [c["title"].replace("Category:", "")
                            for c in p.get("categories", [])]
                if "thumbnail" in p:
                    meta.setdefault(t, [None, None])
                    meta[t][1] = p["thumbnail"]["source"]
            if "continue" in data:
                cont = data["continue"]
            else:
                break
        for t, cl in cats.items():
            m = meta.get(t, [None, None])
            m[0] = classify(cl)
            meta[t] = m
        print(f"  meta {min(i+40,len(titles))}/{len(titles)}", file=sys.stderr)
    return meta


def monthly_views(title):
    enc = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = REST.format(title=enc, start=START, end=END)
    for attempt in range(6):
        r = S.get(url, timeout=30)
        if r.status_code == 404:
            return [0] * len(MONTHS)
        if r.status_code == 429:
            time.sleep(3 + attempt); continue
        r.raise_for_status()
        by_month = {it["timestamp"][:6]: it["views"] for it in r.json().get("items", [])}
        time.sleep(0.1)
        return [by_month.get(m, 0) for m in MONTHS]
    return [0] * len(MONTHS)


def main():
    with open("cats.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    names = [r["name"] for r in rows]

    print("Fetching types + thumbnails...", file=sys.stderr)
    meta = fetch_meta(names)

    print("Fetching monthly pageview series...", file=sys.stderr)
    out = []
    for i, r in enumerate(rows, 1):
        name = r["name"]
        typ, thumb = meta.get(name, ["Other", None])
        out.append({
            "name": name,
            "url": "https://en.wikipedia.org/wiki/" + name.replace(" ", "_"),
            "description": r["description"],
            "word_count": int(r["word_count"]),
            "pageviews": int(r["pageviews_12mo"] or 0),
            "pct_of_cat": float(r["pct_of_Cat"] or 0),
            "type": typ,
            "thumb": thumb,
            "monthly": monthly_views(name),
        })
        if i % 20 == 0:
            print(f"  views {i}/{len(rows)}", file=sys.stderr)

    payload = {
        "generated": time.strftime("%Y-%m-%d"),
        "window": "Jun 2025 - May 2026",
        "months": MONTHS,
        "cat_article_views": 8593151,
        "cats": out,
    }
    with open("cats_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    from collections import Counter
    print("\nType distribution:", file=sys.stderr)
    for t, n in Counter(c["type"] for c in out).most_common():
        print(f"  {n:>3}  {t}", file=sys.stderr)
    missing = sum(1 for c in out if not c["thumb"])
    print(f"\nThumbnails: {len(out)-missing}/{len(out)} have images, "
          f"{missing} use placeholder.", file=sys.stderr)


if __name__ == "__main__":
    main()
