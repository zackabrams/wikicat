#!/usr/bin/env python3
"""Patch cats.csv: re-fetch word counts for rows that came back as 0, drop
non-cat list pages, backfill missing descriptions, and re-rank."""
import csv
import re
import time
import sys
import requests

API = "https://en.wikipedia.org/w/api.php"
S = requests.Session()
S.headers.update({"User-Agent": "longest-cat-finder/1.0 (research script)"})

DROP = {"List of ships' cats"}  # not an individual cat


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


def fetch_one(title):
    """Get full plain-text extract for a single title, following continuation."""
    text = ""
    cont = {}
    while True:
        data = get({
            "action": "query", "prop": "extracts|description",
            "explaintext": 1, "titles": title, "exlimit": "max", **cont,
        })
        page = next(iter(data["query"]["pages"].values()))
        text += page.get("extract", "")
        desc = page.get("description", "")
        if "continue" in data:
            cont = data["continue"]
        else:
            break
    return len(re.findall(r"\b\w+\b", text)), desc


def main():
    rows = []
    with open("cats.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["name"] in DROP:
                continue
            rows.append(row)

    for row in rows:
        if int(row["word_count"]) == 0 or not row["description"]:
            wc, desc = fetch_one(row["name"])
            if int(row["word_count"]) == 0:
                row["word_count"] = wc
                print(f"  fixed {row['name']}: {wc} words", file=sys.stderr)
            if not row["description"] and desc:
                row["description"] = desc

    rows.sort(key=lambda r: int(r["word_count"]), reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i

    with open("cats.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "name", "description", "word_count"])
        w.writeheader()
        w.writerows(rows)
    print(f"Rewrote cats.csv with {len(rows)} rows.", file=sys.stderr)


if __name__ == "__main__":
    main()
