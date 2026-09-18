"""
Scrape the Aesthetics Wiki (aesthetics.fandom.com) via the MediaWiki API and
emit one structured markdown file per aesthetic, plus downloaded images and an
attribution manifest. Output feeds a Claude Code skill.

Content text is CC-BY-SA (see LICENSE). Images each carry their own license,
captured per-image in images/<slug>/credits.json.

Usage:
    python scripts/scrape.py --limit 5                # quick test run
    python scripts/scrape.py --titles "Cottagecore|Cybergoth"
    python scripts/scrape.py                          # full run (all articles)
    python scripts/scrape.py --no-images              # text only
    python scripts/scrape.py --force                  # re-scrape existing files
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import mwparserfromhell
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---- config ----------------------------------------------------------------
API_URL = "https://aesthetics.fandom.com/api.php"
WIKI_BASE = "https://aesthetics.fandom.com"
ARTICLE_BASE = "https://aesthetics.fandom.com/wiki/"
USER_AGENT = (
    "aesthetics-wiki-skill/0.1 (open-source Claude skill; "
    "contact via github repo)"
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AESTHETICS_DIR = os.path.join(ROOT, "aesthetics")
IMAGES_DIR = os.path.join(ROOT, "images")
DATA_DIR = os.path.join(ROOT, "data")

# infobox template names to treat as the aesthetic infobox (lowercased)
INFOBOX_NAMES = {"aesthetic"}

# infobox params we lift into structured frontmatter (source -> output key)
INFOBOX_FIELDS = {
    "other_names": "aka",
    "decade_of_origin": "decade_of_origin",
    "creator_s": "creators",
    "key_motifs": "key_motifs",
    "key_colours": "key_colours",
    "key_colors": "key_colours",
    "key_values": "key_values",
    "related_aesthetics": "related_aesthetics",
    "subgenres": "subgenres",
    "primary_platform": "primary_platform",
    "related_media": "related_media",
}
# fields that should be parsed into lists rather than kept as a single string
LIST_FIELDS = {
    "aka", "key_motifs", "key_colours", "key_values",
    "related_aesthetics", "subgenres", "primary_platform", "related_media",
    "creators",
}

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
SKIP_IMAGE_HINTS = ("site-logo", "wiki-wordmark", "favicon")

RETRIEVED = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---- http ------------------------------------------------------------------
def make_session():
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    retry = Retry(
        total=5, backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=32))
    return s


class BlockedError(RuntimeError):
    """Fandom's Cloudflare refused the request (scripted access blocked)."""


BLOCKED_MSG = (
    "Fandom's Cloudflare blocked scripted API access (HTTP 403). The data in "
    "this repo is a snapshot from 2026-07-22; see README 'Regenerate from source'."
)


def api_get(session, params):
    params = dict(params)
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    params.setdefault("maxlag", "5")
    r = session.get(API_URL, params=params, timeout=60)
    if r.status_code == 403 and "cloudflare" in r.headers.get("server", "").lower():
        raise BlockedError(BLOCKED_MSG)
    r.raise_for_status()
    return r.json()


# ---- discovery -------------------------------------------------------------
def get_all_titles(session):
    """All non-redirect article titles in the main namespace."""
    titles = []
    apcontinue = None
    while True:
        params = {
            "action": "query", "list": "allpages", "apnamespace": "0",
            "aplimit": "500", "apfilterredir": "nonredirects",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue
        data = api_get(session, params)
        titles.extend(p["title"] for p in data["query"]["allpages"])
        cont = data.get("continue")
        if not cont:
            break
        apcontinue = cont["apcontinue"]
    return titles


# ---- helpers ---------------------------------------------------------------
def slugify(title):
    s = title.strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "untitled"


def strip_wiki(text):
    """Wikitext fragment -> readable plaintext (resolve links, drop markup)."""
    if not text:
        return ""
    code = mwparserfromhell.parse(text)
    return code.strip_code().strip()


def _split_top_commas(text):
    """Split on commas that sit at paren/bracket depth 0."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch in "([":
            depth += 1
            cur.append(ch)
        elif ch in ")]":
            depth = max(0, depth - 1)
            cur.append(ch)
        elif ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


def split_list(raw):
    """Split an infobox list field (separated by <br>, newlines, commas)."""
    if not raw:
        return []
    out = []
    for seg in re.split(r"<\s*br\s*/?\s*>|\n", raw):
        val = strip_wiki(seg).strip(" ,;")
        if val:
            out.extend(_split_top_commas(val))
    # de-dupe, preserve order
    seen, result = set(), []
    for v in out:
        k = v.lower()
        if k not in seen:
            seen.add(k)
            result.append(v)
    return result


def parse_infobox(wikitext):
    """Extract the {{Aesthetic}} infobox params into a structured dict."""
    code = mwparserfromhell.parse(wikitext)
    for tmpl in code.filter_templates():
        name = str(tmpl.name).strip().lower()
        if name in INFOBOX_NAMES:
            out = {}
            for src, dst in INFOBOX_FIELDS.items():
                if tmpl.has(src):
                    raw = str(tmpl.get(src).value).strip()
                    if not raw:
                        continue
                    if dst in LIST_FIELDS:
                        out[dst] = split_list(raw)
                    else:
                        out[dst] = strip_wiki(raw)
            return out
    return {}


def html_to_markdown(html):
    """Rendered article HTML -> clean markdown body (no infobox, no chrome)."""
    soup = BeautifulSoup(html, "html.parser")
    # drop infobox (captured in frontmatter), edit links, toc, nav, galleries
    for sel in ["aside", ".mw-editsection", ".toc", "#toc", ".navbox",
                ".portable-infobox", "table.infobox", ".reference",
                ".mw-references-wrap", "style", "script"]:
        for el in soup.select(sel):
            el.decompose()
    # inline images are collected separately; drop them from the body text
    for img in soup.find_all("img"):
        img.decompose()
    for fig in soup.find_all(["figure", "figcaption"]):
        fig.decompose()
    # absolutise internal links so the markdown is portable
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/wiki/"):
            a["href"] = WIKI_BASE + href
        elif href.startswith("#"):
            a.unwrap()
    body = md(str(soup), heading_style="ATX", strip=["img"])
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


def collect_image_meta(session, file_titles):
    """imageinfo (url + license/artist) for a list of File: titles, batched."""
    meta = {}
    file_titles = [t for t in file_titles if t]
    for i in range(0, len(file_titles), 50):
        batch = file_titles[i:i + 50]
        titles = "|".join("File:" + t for t in batch)
        data = api_get(session, {
            "action": "query", "titles": titles, "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
        })
        for page in data.get("query", {}).get("pages", []):
            info = page.get("imageinfo")
            if not info:
                continue
            ii = info[0]
            ext = ii.get("extmetadata", {})
            fname = page["title"].split(":", 1)[-1]
            meta[fname] = {
                "url": ii.get("url"),
                "descriptionurl": ii.get("descriptionurl"),
                "mime": ii.get("mime"),
                "width": ii.get("width"),
                "height": ii.get("height"),
                "artist": strip_html(ext.get("Artist", {}).get("value")),
                "license": ext.get("LicenseShortName", {}).get("value"),
                "license_url": ext.get("LicenseUrl", {}).get("value"),
                "description": strip_html(
                    ext.get("ImageDescription", {}).get("value")),
            }
    return meta


def strip_html(val):
    if not val:
        return None
    return BeautifulSoup(val, "html.parser").get_text(" ", strip=True) or None


def wanted_image(fname):
    low = fname.lower()
    if not low.endswith(IMAGE_EXTS):
        return False
    return not any(h in low for h in SKIP_IMAGE_HINTS)


def download_image(session, url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True
    try:
        with session.get(url, timeout=90, stream=True) as r:
            r.raise_for_status()
            tmp = dest + ".part"
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
            os.replace(tmp, dest)
        return True
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("  image fail %s: %s\n" % (url, exc))
        return False


# ---- frontmatter -----------------------------------------------------------
def yaml_scalar(v):
    v = str(v).replace('"', '\\"')
    return '"%s"' % v


def yaml_list(items):
    return "[%s]" % ", ".join(yaml_scalar(i) for i in items)


def build_frontmatter(fm):
    lines = ["---"]
    for k, v in fm.items():
        if v is None or v == "" or v == []:
            continue
        if isinstance(v, bool):
            lines.append("%s: %s" % (k, "true" if v else "false"))
        elif isinstance(v, int):
            lines.append("%s: %d" % (k, v))
        elif isinstance(v, list):
            lines.append("%s: %s" % (k, yaml_list(v)))
        else:
            lines.append("%s: %s" % (k, yaml_scalar(v)))
    lines.append("---")
    return "\n".join(lines)


def first_sentence(body):
    text = re.sub(r"\s+", " ", body).strip()
    m = re.match(r"(.{0,300}?[.!?])(\s|$)", text)
    return (m.group(1) if m else text[:300]).strip()


# ---- per-page --------------------------------------------------------------
def scrape_page(session, title, download_images=True, force=False):
    slug = slugify(title)
    out_path = os.path.join(AESTHETICS_DIR, slug + ".md")
    if os.path.exists(out_path) and not force:
        return {"slug": slug, "title": title, "status": "skipped"}

    parse = api_get(session, {
        "action": "parse", "page": title,
        "prop": "wikitext|text|images|displaytitle", "redirects": "1",
    }).get("parse", {})
    wikitext = parse.get("wikitext", "")
    html = parse.get("text", "")
    image_files = [f for f in parse.get("images", []) if wanted_image(f)]

    infobox = parse_infobox(wikitext)
    body = html_to_markdown(html)

    # images
    img_records = []
    if image_files:
        meta = collect_image_meta(session, image_files)
        img_dir = os.path.join(IMAGES_DIR, slug)
        if download_images:
            os.makedirs(img_dir, exist_ok=True)
        for fname in image_files:
            m = meta.get(fname)
            if not m or not m.get("url"):
                continue
            local = os.path.join("images", slug, fname)
            rec = {
                "file": fname, "local": local, "source_url": m["url"],
                "page": m.get("descriptionurl"), "artist": m.get("artist"),
                "license": m.get("license"), "license_url": m.get("license_url"),
                "description": m.get("description"),
            }
            if download_images:
                ok = download_image(session, m["url"],
                                    os.path.join(IMAGES_DIR, slug, fname))
                rec["downloaded"] = ok
            img_records.append(rec)
        if download_images and img_records:
            with open(os.path.join(img_dir, "credits.json"), "w") as f:
                json.dump(img_records, f, indent=2, ensure_ascii=False)

    # assemble markdown
    source_url = ARTICLE_BASE + title.replace(" ", "_")
    fm = {"name": title, "slug": slug}
    fm.update(infobox)
    fm["source_url"] = source_url
    fm["license"] = "CC-BY-SA-4.0"
    fm["retrieved"] = RETRIEVED
    fm["image_count"] = len(img_records)

    parts = [build_frontmatter(fm), "", "# " + title, ""]
    if infobox.get("aka"):
        parts.append("_Also known as: %s_" % ", ".join(infobox["aka"]))
        parts.append("")
    parts.append(body if body else "_No article body._")
    if img_records:
        parts.append("\n## Images\n")
        for rec in img_records:
            cap = rec.get("description") or ""
            credit = " ".join(x for x in [rec.get("artist"),
                              rec.get("license")] if x)
            line = "- `%s`" % rec["local"]
            if cap:
                line += " " + cap
            if credit:
                line += " (%s)" % credit
            parts.append(line)
    parts.append("\n## Source and attribution\n")
    parts.append(
        'Text adapted from "%s" on the Aesthetics Wiki '
        "(%s), licensed CC-BY-SA 4.0. Retrieved %s. "
        "Images retain their individual licenses; see the local "
        "`credits.json`." % (title, source_url, RETRIEVED)
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts).rstrip() + "\n")

    return {
        "slug": slug, "title": title, "status": "ok",
        "summary": first_sentence(body),
        "aka": infobox.get("aka", []),
        "decade_of_origin": infobox.get("decade_of_origin"),
        "key_colours": infobox.get("key_colours", []),
        "related_aesthetics": infobox.get("related_aesthetics", []),
        "subgenres": infobox.get("subgenres", []),
        "image_count": len(img_records),
        "has_infobox": bool(infobox),
    }


# ---- driver ----------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--titles", type=str, default="")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    os.makedirs(AESTHETICS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    session = make_session()

    if args.titles:
        titles = [t.strip() for t in args.titles.split("|") if t.strip()]
    else:
        print("Fetching article list ...", flush=True)
        try:
            titles = get_all_titles(session)
        except BlockedError as exc:
            sys.exit(str(exc))
        print("  %d articles" % len(titles), flush=True)
    if args.limit:
        titles = titles[:args.limit]

    download_images = not args.no_images
    results, failures = [], []
    start = time.time()
    done = 0
    total = len(titles)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(scrape_page, session, t, download_images, args.force): t
            for t in titles
        }
        for fut in as_completed(futs):
            title = futs[fut]
            done += 1
            try:
                res = fut.result()
                if res["status"] != "skipped":
                    results.append(res)
            except Exception as exc:  # noqa: BLE001
                failures.append({"title": title, "error": str(exc)})
                sys.stderr.write("PAGE FAIL %s: %s\n" % (title, exc))
            if done % 25 == 0 or done == total:
                rate = done / max(time.time() - start, 1e-6)
                print("  %d/%d  (%.1f/s)  fails=%d"
                      % (done, total, rate, len(failures)), flush=True)

    if failures:
        with open(os.path.join(DATA_DIR, "failures.json"), "w") as f:
            json.dump(failures, f, indent=2, ensure_ascii=False)

    # rebuild the authoritative search index from the written files
    try:
        import build_index
        build_index.main()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("index build failed (run build_index.py): %s\n" % exc)

    elapsed = time.time() - start
    ok = len([r for r in results if r.get("status") == "ok"])
    print("\nDone. ok=%d fails=%d  %.0fs" % (ok, len(failures), elapsed),
          flush=True)


if __name__ == "__main__":
    main()
