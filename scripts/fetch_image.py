"""
Fetch reference image(s) for one aesthetic on demand, so the model can view
them locally without the repo committing image binaries.

Every aesthetic ships an images/<slug>/credits.json manifest (source URL per
image) even when the binaries are not committed. This downloads the matching
files into images/<slug>/ and prints the local paths to Read.

    python scripts/fetch_image.py cottagecore            # first few images
    python scripts/fetch_image.py cottagecore --all      # every image
    python scripts/fetch_image.py cottagecore --name book  # only matches "book"
    python scripts/fetch_image.py cottagecore --limit 1   # just the cover image
"""

import argparse
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(ROOT, "images")
USER_AGENT = "aesthetics-wiki-skill/0.1 (on-demand image fetch)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--name", help="only images whose filename contains this")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=4)
    args = ap.parse_args()

    slug_dir = os.path.join(IMAGES_DIR, args.slug)
    manifest = os.path.join(slug_dir, "credits.json")
    if not os.path.exists(manifest):
        sys.exit("no manifest for '%s' (expected %s)" % (args.slug, manifest))

    with open(manifest, encoding="utf-8") as f:
        records = json.load(f)
    if args.name:
        needle = args.name.lower()
        records = [r for r in records if needle in r["file"].lower()]
    if not args.all:
        records = records[:args.limit]

    os.makedirs(slug_dir, exist_ok=True)
    paths = []
    for rec in records:
        dest = os.path.join(slug_dir, rec["file"])
        if not (os.path.exists(dest) and os.path.getsize(dest) > 0):
            req = urllib.request.Request(rec["source_url"],
                                         headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=60) as r, \
                        open(dest, "wb") as out:
                    out.write(r.read())
            except Exception as exc:  # noqa: BLE001
                sys.stderr.write("fail %s: %s\n" % (rec["file"], exc))
                continue
        paths.append(os.path.join("images", args.slug, rec["file"]))

    for p in paths:
        print(p)
    if not paths:
        sys.exit("nothing fetched")


if __name__ == "__main__":
    main()
