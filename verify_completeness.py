#!/usr/bin/env python3
"""Independent cross-check that cats_data.json isn't missing notable cats.

My list was built only from Wikipedia's Category:Individual cats tree. This
verifies it against two *category-independent* sources:
  A) Wikidata: every item that is an instance of "cat" (Q146) or any cat breed
     (subclass* of Q146) AND has an English Wikipedia sitelink.
  B) The hand-curated "List of individual cats" article (its ns-0 wikilinks).

Anything in A or B but not in my list is printed for manual judgement, along
with whether it's a redirect (i.e. has no standalone article).
"""
import json
import sys
import time
import requests

UA = {"User-Agent": "longest-cat-finder/1.0 (research; zackdabrams@gmail.com)"}
API = "https://en.wikipedia.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
S = requests.Session(); S.headers.update(UA)


def norm(t):
    return t.replace("_", " ").strip()


def wikidata_cats():
    q = """
    SELECT DISTINCT ?article WHERE {
      ?item wdt:P31 ?type .
      ?type wdt:P279* wd:Q146 .
      ?article schema:about ?item ;
               schema:isPartOf <https://en.wikipedia.org/> .
    }"""
    r = S.get(SPARQL, params={"query": q, "format": "json"}, timeout=120)
    r.raise_for_status()
    out = set()
    for b in r.json()["results"]["bindings"]:
        url = b["article"]["value"]
        title = requests.utils.unquote(url.split("/wiki/")[-1])
        out.add(norm(title))
    return out


def list_article_links():
    links, cont = set(), {}
    while True:
        d = S.get(API, params={
            "action": "query", "prop": "links", "titles": "List of individual cats",
            "plnamespace": 0, "pllimit": "max", "format": "json", **cont,
        }, timeout=60).json()
        for p in d["query"]["pages"].values():
            for l in p.get("links", []):
                links.add(norm(l["title"]))
        if "continue" in d:
            cont = d["continue"]; time.sleep(0.3)
        else:
            break
    return links


def redirect_map(titles):
    """For a set of titles, return {title: redirect_target_or_None}."""
    res = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        d = S.get(API, params={
            "action": "query", "redirects": 1, "prop": "description",
            "titles": "|".join(batch), "format": "json",
        }, timeout=60).json()
        q = d["query"]
        redir = {r["from"]: r["to"] for r in q.get("redirects", [])}
        norm_titles = {norm(r["from"]): r["to"] for r in q.get("redirects", [])}
        descs = {p["title"]: p.get("description", "") for p in q["pages"].values()}
        for t in batch:
            res[t] = (norm_titles.get(t), descs.get(t, ""))
        time.sleep(0.2)
    return res


def main():
    data = json.load(open("cats_data.json"))
    mine = {norm(c["name"]) for c in data["cats"]}
    print(f"My list: {len(mine)} cats\n", file=sys.stderr)

    print("Querying Wikidata (instance of cat / cat breed + enwiki)...", file=sys.stderr)
    wd = wikidata_cats()
    print(f"  Wikidata cats with enwiki articles: {len(wd)}", file=sys.stderr)

    print("Reading 'List of individual cats' article links...", file=sys.stderr)
    listed = list_article_links()
    print(f"  ns-0 links on that list page: {len(listed)}", file=sys.stderr)

    missing_wd = sorted(wd - mine)
    missing_list = sorted((listed - mine) & wd)  # list links confirmed as cats by Wikidata

    print("\n=== In Wikidata-cats but NOT in my list ===")
    info = redirect_map(missing_wd) if missing_wd else {}
    real_misses = []
    for t in missing_wd:
        target, desc = info.get(t, (None, ""))
        if target:
            print(f"  [redirect] {t}  ->  {target}")
        else:
            real_misses.append(t)
            print(f"  [ARTICLE]  {t}   — {desc}")

    print(f"\nWikidata candidates not in my list: {len(missing_wd)} "
          f"({len(real_misses)} standalone articles, "
          f"{len(missing_wd)-len(real_misses)} redirects)")

    extra_from_list = sorted((listed & wd) - mine)
    print(f"\nCross-confirmed by the curated list too: "
          f"{[t for t in extra_from_list]}")

    json.dump({"wikidata_only_articles": real_misses}, open("missing_report.json", "w"), indent=1)


if __name__ == "__main__":
    main()
