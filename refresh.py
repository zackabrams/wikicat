#!/usr/bin/env python3
"""Monthly data refresh (run by GitHub Actions).

Re-fetches pageviews (total + monthly sparkline) and word counts for the
existing roster in cats_data.json over a *rolling* 12-month window, and
recomputes the 'Cat' baseline. Deliberately preserves each cat's name, url,
description, type, and thumbnail so manual curation (e.g. corrected photos)
is never clobbered. New cats are added separately via add_cats.py.
"""
import csv
import json
import re
import sys
import time
import build_data as B  # reuse get(), monthly_views(), dynamic window


def word_counts(titles):
    """Plain-text word count per title, batched; follows extract continuation."""
    counts = {}
    for i in range(0, len(titles), 20):
        batch = titles[i:i + 20]
        cont = {}
        while True:
            data = B.get({"action": "query", "prop": "extracts", "explaintext": 1,
                          "exlimit": "max", "redirects": 1,
                          "titles": "|".join(batch), **cont})
            for p in data.get("query", {}).get("pages", {}).values():
                if "extract" in p:
                    counts[p["title"]] = len(re.findall(r"\b\w+\b", p["extract"]))
            if "continue" in data:
                cont = data["continue"]
            else:
                break
        print(f"  word counts {min(i+20, len(titles))}/{len(titles)}", file=sys.stderr)
    return counts


def main():
    data = json.load(open("cats_data.json"))
    cats = data["cats"]
    names = [c["name"] for c in cats]
    print(f"Refreshing {len(names)} cats over window {B.WINDOW_LABEL}", file=sys.stderr)

    baseline = sum(B.monthly_views("Cat"))
    print(f"  Cat baseline: {baseline:,}", file=sys.stderr)

    wc = word_counts(names)

    for i, c in enumerate(cats, 1):
        m = B.monthly_views(c["name"])
        c["monthly"] = m
        c["pageviews"] = sum(m)
        c["pct_of_cat"] = round(100 * sum(m) / baseline, 3) if baseline else 0
        # word count: redirects resolve to a different title key; fall back to old value
        c["word_count"] = wc.get(c["name"], c["word_count"])
        if i % 25 == 0:
            print(f"  views {i}/{len(cats)}", file=sys.stderr)

    cats.sort(key=lambda c: c["word_count"], reverse=True)
    data["cat_article_views"] = baseline
    data["window"] = B.WINDOW_LABEL
    data["months"] = B.MONTHS
    data["generated"] = time.strftime("%Y-%m-%d")
    json.dump(data, open("cats_data.json", "w"), ensure_ascii=False, indent=1)

    def write_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["rank", "name", "description", "word_count",
                        "pageviews_12mo", "pct_of_Cat"])
            for i, c in enumerate(rows, 1):
                w.writerow([i, c["name"], c["description"], c["word_count"],
                            c["pageviews"], c["pct_of_cat"]])
    write_csv("cats.csv", cats)
    write_csv("cats_by_popularity.csv",
              sorted(cats, key=lambda c: c["pageviews"], reverse=True))
    print(f"\nRefreshed {len(cats)} cats. Top: {cats[0]['name']} "
          f"({cats[0]['word_count']:,} words).", file=sys.stderr)


if __name__ == "__main__":
    main()
