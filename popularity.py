#!/usr/bin/env python3
"""Enrich cats.csv with pageview popularity data from the Wikimedia Pageviews API.

Adds:
  pageviews_12mo  - total views over the last 12 complete months
  pct_of_Cat      - those views as a percentage of the general "Cat" article
"""
import csv
import time
import sys
import urllib.parse
import requests

REST = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        "en.wikipedia/all-access/all-agents/{title}/monthly/{start}/{end}")
S = requests.Session()
S.headers.update({"User-Agent": "longest-cat-finder/1.0 (research; zackdabrams@gmail.com)"})

# Last 12 complete months. Today is 2026-06-23 -> window 2025-06 .. 2026-05.
START = "2025060100"
END = "2026053100"


def pageviews(title):
    """Total monthly pageviews for an article title over the window."""
    enc = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = REST.format(title=enc, start=START, end=END)
    for attempt in range(6):
        r = S.get(url, timeout=30)
        if r.status_code == 404:
            return 0  # no data for this title/window
        if r.status_code == 429:
            time.sleep(3 + attempt)
            continue
        r.raise_for_status()
        items = r.json().get("items", [])
        time.sleep(0.1)
        return sum(it["views"] for it in items)
    return None


def main():
    with open("cats.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print("Fetching baseline: 'Cat' article...", file=sys.stderr)
    cat_total = pageviews("Cat")
    print(f"  Cat article 12-mo views: {cat_total:,}", file=sys.stderr)

    for i, row in enumerate(rows, 1):
        v = pageviews(row["name"])
        row["pageviews_12mo"] = v if v is not None else ""
        row["pct_of_Cat"] = (round(100 * v / cat_total, 3)
                             if v and cat_total else 0)
        if i % 20 == 0:
            print(f"  {i}/{len(rows)} done", file=sys.stderr)

    fields = ["rank", "name", "description", "word_count",
              "pageviews_12mo", "pct_of_Cat"]
    with open("cats.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # also write a copy sorted by popularity for convenience
    rows_by_pop = sorted(rows, key=lambda r: int(r["pageviews_12mo"] or 0),
                         reverse=True)
    with open("cats_by_popularity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for j, r in enumerate(rows_by_pop, 1):
            r2 = dict(r); r2["rank"] = j
            w.writerow(r2)

    print(f"\nBaseline 'Cat' article: {cat_total:,} views (12 mo)", file=sys.stderr)
    print("Most popular cats:", file=sys.stderr)
    for r in rows_by_pop[:10]:
        print(f"  {int(r['pageviews_12mo'] or 0):>10,}  "
              f"({r['pct_of_Cat']}% of Cat)  {r['name']}", file=sys.stderr)


if __name__ == "__main__":
    main()
