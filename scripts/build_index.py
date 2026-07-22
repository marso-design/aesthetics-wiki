"""
Build data/index.json from the scraped aesthetics/*.md files.

This is the source of truth for the lookup CLI. It parses each file's
frontmatter (emitted as JSON-compatible YAML, so no YAML dependency needed)
and derives a short summary from the body. Re-run any time after scraping.

    python scripts/build_index.py
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AESTHETICS_DIR = os.path.join(ROOT, "aesthetics")
DATA_DIR = os.path.join(ROOT, "data")

# frontmatter keys carried into the index
INDEX_KEYS = [
    "name", "slug", "aka", "decade_of_origin", "key_motifs", "key_colours",
    "palette", "key_values", "related_aesthetics", "subgenres",
    "primary_platform", "related_media", "source_url", "image_count",
]

# body paragraphs to skip when picking a summary
SKIP_PREFIXES = ("#", ">", "_", "!", "|", "[", "*Also", "**Reason")
SKIP_CONTAINS = ("Sensitive Content Notice", "following article contains",
                 "Content Warning", "may be distressing")


def parse_frontmatter(text):
    """Return (frontmatter_dict, body). Values are JSON, so json.loads them."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    block = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    fm = {}
    for line in block.splitlines():
        if ": " not in line:
            continue
        key, _, raw = line.partition(": ")
        try:
            fm[key.strip()] = json.loads(raw.strip())
        except (ValueError, json.JSONDecodeError):
            fm[key.strip()] = raw.strip().strip('"')
    return fm, body


def pick_summary(body, limit=320):
    for para in re.split(r"\n\s*\n", body):
        p = para.strip()
        if len(p) < 40:
            continue
        if p.startswith(SKIP_PREFIXES):
            continue
        if any(s in p for s in SKIP_CONTAINS):
            continue
        p = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", p)   # unlink markdown links
        p = re.sub(r"\*\*([^*]+)\*\*", r"\1", p)          # de-bold
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) <= limit:
            return p
        cut = p[:limit]
        dot = cut.rfind(". ")
        return (cut[:dot + 1] if dot > 80 else cut).strip()
    return ""


def main():
    rows = []
    for fn in sorted(os.listdir(AESTHETICS_DIR)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(AESTHETICS_DIR, fn)
        with open(path, encoding="utf-8") as f:
            fm, body = parse_frontmatter(f.read())
        if not fm.get("slug"):
            continue
        row = {k: fm[k] for k in INDEX_KEYS if k in fm}
        if "image_count" in row:
            try:
                row["image_count"] = int(row["image_count"])
            except (TypeError, ValueError):
                row["image_count"] = 0
        row["file"] = os.path.join("aesthetics", fn)
        row["summary"] = pick_summary(body)
        rows.append(row)

    rows.sort(key=lambda r: r.get("name", "").lower())
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    with_infobox = sum(1 for r in rows if r.get("key_colours")
                       or r.get("related_aesthetics"))
    total_imgs = sum(r.get("image_count", 0) for r in rows)
    print("index rows: %d" % len(rows))
    print("with structured infobox: %d" % with_infobox)
    print("total images referenced: %d" % total_imgs)


if __name__ == "__main__":
    main()
