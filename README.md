# 🐱 The Longest-Page Cats of Wikipedia

Every individual cat with an English Wikipedia article, ranked by **how long that
article is** and **how many people actually read it**.

👉 **Live page:** `index.html` (sortable table, search, type filter, thumbnails,
per-cat 12-month traffic sparklines).

The headline finding: **Larry**, Chief Mouser to the UK Cabinet Office, wins on
*both* counts — longest article (2,270 words) and most-viewed (~592k views/year,
about 6.9% of the traffic the general [Cat](https://en.wikipedia.org/wiki/Cat)
article gets).

## Data

- **Source:** articles under Wikipedia's
  [Category:Individual cats](https://en.wikipedia.org/wiki/Category:Individual_cats)
  (recursively, minus redirects and non-cat list pages), plus a Wikidata
  cross-check that recovered notable cats filed under sibling categories
  (Chief mousers, Animal actors, Cat artists) — **116 cats**.
- **Word count:** plain-text prose from the MediaWiki `extracts` API (excludes
  infobox, references, captions).
- **Popularity:** total views over Jun 2025 – May 2026 from the
  [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/).
- **Type / images:** derived from each article's Wikipedia categories and
  `pageimages` thumbnails.

Tabular exports: [`cats.csv`](cats.csv) (by length) and
[`cats_by_popularity.csv`](cats_by_popularity.csv) (by views).

## Rebuild from scratch

```bash
python3 longest_cat.py     # gather cats + word counts  -> cats.csv
python3 finalize_cats.py   # drop redirects, tidy descriptions
python3 popularity.py      # add pageview columns
python3 build_data.py      # add types, thumbnails, monthly series -> cats_data.json
python3 verify_completeness.py  # cross-check vs Wikidata for missed cats
python3 add_cats.py        # merge in any notable cats found outside the category
# open index.html (served over http, e.g. `python3 serve.py`)
```

## Publish to GitHub Pages

```bash
# create a repo on github.com (e.g. "wikicat"), then:
git remote add origin https://github.com/<you>/wikicat.git
git push -u origin main
# GitHub → repo Settings → Pages → Source: "Deploy from a branch" → main / root
```

Your page goes live at `https://<you>.github.io/wikicat/`.

---
Cat photos and article text © their respective authors, via Wikimedia.
