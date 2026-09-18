"""
Query the aesthetics index. This is the fast path for the Claude skill:
resolve a name, search by colour/decade/motif, or list neighbours, without
loading the whole dataset into context.

    python scripts/lookup.py <query>          # smart search (name, then full-text)
    python scripts/lookup.py --get cottagecore
    python scripts/lookup.py --find "green forest"
    python scripts/lookup.py --color pastel
    python scripts/lookup.py --decade 1990s
    python scripts/lookup.py --motif mushroom
    python scripts/lookup.py --related Cottagecore
    python scripts/lookup.py --list
    python scripts/lookup.py --stats
Add --json for machine-readable output, --limit N to cap results.
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "data", "index.json")

TEXT_FIELDS = ["name", "aka", "summary", "key_motifs", "key_colours",
               "key_values", "related_aesthetics", "subgenres",
               "primary_platform", "related_media"]


def load():
    if not os.path.exists(INDEX):
        sys.exit("index not found. Run: python scripts/build_index.py")
    with open(INDEX, encoding="utf-8") as f:
        return json.load(f)


def as_text(row, fields=TEXT_FIELDS):
    chunks = []
    for k in fields:
        v = row.get(k)
        if isinstance(v, list):
            chunks.extend(str(x) for x in v)
        elif v:
            chunks.append(str(v))
    return " ␟ ".join(chunks).lower()


def resolve(rows, name):
    key = name.strip().lower()
    by_slug = {r["slug"]: r for r in rows}
    if key in by_slug:
        return by_slug[key]
    for r in rows:
        if r.get("name", "").lower() == key:
            return r
    for r in rows:
        if any(a.lower() == key for a in r.get("aka", [])):
            return r
    hits = [r for r in rows if key in r.get("name", "").lower()]
    return hits[0] if len(hits) == 1 else None


def field_search(rows, field, needle):
    n = needle.strip().lower()
    out = []
    for r in rows:
        v = r.get(field)
        vals = v if isinstance(v, list) else ([v] if v else [])
        if any(n in str(x).lower() for x in vals):
            out.append(r)
    return out


def full_text(rows, query):
    terms = [t for t in query.strip().lower().split() if t]
    scored = []
    for r in rows:
        blob = as_text(r)
        name = r.get("name", "").lower()
        score = sum(blob.count(t) for t in terms)
        if query.strip().lower() in name:
            score += 50
        if all(t in blob for t in terms):
            score += 5
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1].get("name", "")))
    return [r for _, r in scored]


def fmt(row, verbose=False):
    line = "%-28s %s" % (row.get("name", "?"), row.get("file", ""))
    if not verbose:
        return line
    parts = [line]
    if row.get("aka"):
        parts.append("  aka: " + ", ".join(row["aka"]))
    for k in ["decade_of_origin", "key_colours", "key_motifs",
              "related_aesthetics", "subgenres"]:
        v = row.get(k)
        if v:
            v = ", ".join(v) if isinstance(v, list) else v
            parts.append("  %s: %s" % (k, v))
    if row.get("summary"):
        parts.append("  " + row["summary"])
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="*")
    ap.add_argument("--get")
    ap.add_argument("--find")
    ap.add_argument("--color", "--colour", dest="color")
    ap.add_argument("--decade")
    ap.add_argument("--motif")
    ap.add_argument("--related")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = load()

    def emit(items, verbose=False):
        if args.json:
            print(json.dumps(items, indent=2, ensure_ascii=False))
        else:
            for r in items[:args.limit]:
                print(fmt(r, verbose))
            if len(items) > args.limit:
                print("... %d more (raise --limit)" % (len(items) - args.limit))

    if args.stats:
        print("aesthetics: %d" % len(rows))
        print("with colours: %d" % sum(1 for r in rows if r.get("key_colours")))
        print("with palettes: %d" % sum(1 for r in rows if r.get("palette")))
        return
    if args.list:
        for r in rows:
            print("%-32s %s" % (r["slug"], r.get("name", "")))
        return
    if args.get:
        r = resolve(rows, args.get)
        if not r:
            hits = full_text(rows, args.get)[:args.limit]
            print("no exact match. closest:" if hits else "no match.")
            emit(hits)
            return
        print(json.dumps(r, indent=2, ensure_ascii=False) if args.json
              else fmt(r, verbose=True))
        return
    if args.related:
        r = resolve(rows, args.related)
        if not r:
            sys.exit("unknown aesthetic: " + args.related)
        names = r.get("related_aesthetics", []) + r.get("subgenres", [])
        emit([resolve(rows, n) or {"name": n, "file": "(not scraped)"}
              for n in names])
        return
    if args.color:
        emit(field_search(rows, "key_colours", args.color), verbose=True)
        return
    if args.decade:
        emit(field_search(rows, "decade_of_origin", args.decade), verbose=True)
        return
    if args.motif:
        emit(field_search(rows, "key_motifs", args.motif), verbose=True)
        return
    if args.find:
        emit(full_text(rows, args.find), verbose=True)
        return

    query = " ".join(args.query).strip()
    if not query:
        ap.print_help()
        return
    r = resolve(rows, query)
    if r:
        print(json.dumps(r, indent=2, ensure_ascii=False) if args.json
              else fmt(r, verbose=True))
    else:
        emit(full_text(rows, query), verbose=True)


if __name__ == "__main__":
    main()
