#!/usr/bin/env python3
"""Add specific cat articles (found via the Wikidata cross-check) to the dataset,
fetching the same fields as the main pipeline, then re-rank and rewrite outputs."""
import csv
import json
import re
import sys
import build_data as B  # reuse get(), classify(), monthly_views(), MONTHS

NEW = ["Freya (cat)", "Orangey", "Mugi the Cat"]


def enrich(title):
    # full plain-text extract -> word count; + Wikidata short description
    d = B.get({"action": "query", "prop": "extracts|description|categories|pageimages",
               "explaintext": 1, "redirects": 1, "cllimit": "max", "clshow": "!hidden",
               "piprop": "thumbnail", "pithumbsize": "200", "titles": title})
    p = next(iter(d["query"]["pages"].values()))
    text = p.get("extract", "")
    wc = len(re.findall(r"\b\w+\b", text))
    desc = p.get("description", "")
    if not desc:
        m = re.match(r".*?[.!?](?=\s|$)", text.strip(), re.S)
        desc = (m.group(0) if m else text[:120]).replace("\n", " ").strip()
    cats = [c["title"].replace("Category:", "") for c in p.get("categories", [])]
    thumb = p["thumbnail"]["source"] if "thumbnail" in p else None
    monthly = B.monthly_views(title)
    return {
        "name": title,
        "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
        "description": desc,
        "word_count": wc,
        "pageviews": sum(monthly),
        "type": B.classify(cats),
        "thumb": thumb,
        "monthly": monthly,
    }


def main():
    data = json.load(open("cats_data.json"))
    have = {c["name"] for c in data["cats"]}
    baseline = data["cat_article_views"]

    for t in NEW:
        if t in have:
            print(f"  skip (already present): {t}", file=sys.stderr); continue
        c = enrich(t)
        c["pct_of_cat"] = round(100 * c["pageviews"] / baseline, 3) if baseline else 0
        data["cats"].append(c)
        print(f"  added {t}: {c['word_count']} words, {c['pageviews']:,} views, "
              f"type={c['type']}, img={'yes' if c['thumb'] else 'no'}", file=sys.stderr)

    data["cats"].sort(key=lambda c: c["word_count"], reverse=True)
    data["generated"] = B.time.strftime("%Y-%m-%d")
    json.dump(data, open("cats_data.json", "w"), ensure_ascii=False, indent=1)

    # rewrite CSVs from merged data
    def write_csv(path, rows):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["rank", "name", "description", "word_count",
                        "pageviews_12mo", "pct_of_Cat"])
            for i, c in enumerate(rows, 1):
                w.writerow([i, c["name"], c["description"], c["word_count"],
                            c["pageviews"], c["pct_of_cat"]])
    write_csv("cats.csv", data["cats"])
    write_csv("cats_by_popularity.csv",
              sorted(data["cats"], key=lambda c: c["pageviews"], reverse=True))
    print(f"\nDataset now has {len(data['cats'])} cats.", file=sys.stderr)


if __name__ == "__main__":
    main()
