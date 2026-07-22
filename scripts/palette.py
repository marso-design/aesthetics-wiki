"""
Derive a real hex colour palette for each aesthetic from its downloaded
reference images, so "earthy tones" becomes #6B4F3A / #7A8450 / #E8DCC0.

Writes data/palettes.json and injects a `palette` field into each
aesthetics/<slug>.md front matter. The palettes are committed even though the
image binaries are not, so the design value ships without the 2 GB.

Requires locally downloaded images (run scripts/scrape.py first). Aesthetics
with no local images are skipped.

    python scripts/palette.py                 # all aesthetics
    python scripts/palette.py --slug vaporwave
    python scripts/palette.py --limit 20 --colors 6 --images-per 6
    python scripts/palette.py --no-inject     # only write data/palettes.json
"""

import argparse
import json
import os
import re

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AESTHETICS_DIR = os.path.join(ROOT, "aesthetics")
IMAGES_DIR = os.path.join(ROOT, "images")
DATA_DIR = os.path.join(ROOT, "data")

IMG_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")


def load_rgb(path, size):
    """Open an image, flatten transparency onto white, return a size x size RGB."""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im).convert("RGB")
    else:
        im = im.convert("RGB")
    return im.resize((size, size))


def image_paths(slug, images_per):
    """First N locally present images for a slug, in manifest order."""
    slug_dir = os.path.join(IMAGES_DIR, slug)
    manifest = os.path.join(slug_dir, "credits.json")
    files = []
    if os.path.exists(manifest):
        with open(manifest, encoding="utf-8") as f:
            files = [r["file"] for r in json.load(f)]
    else:
        files = sorted(os.listdir(slug_dir)) if os.path.isdir(slug_dir) else []
    out = []
    for name in files:
        if not name.lower().endswith(IMG_EXTS):
            continue
        p = os.path.join(slug_dir, name)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            out.append(p)
        if len(out) >= images_per:
            break
    return out


def hexof(rgb):
    return "#%02X%02X%02X" % tuple(rgb)


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def extract_palette(paths, colors, size):
    """Dominant colours across the given images, ranked by coverage."""
    montage = Image.new("RGB", (size, size * len(paths)))
    used = 0
    for p in paths:
        try:
            montage.paste(load_rgb(p, size), (0, size * used))
            used += 1
        except Exception:  # noqa: BLE001
            continue
    if not used:
        return []
    if used < len(paths):
        montage = montage.crop((0, 0, size, size * used))

    # over-quantize, then merge near-duplicates down to `colors`
    q = montage.quantize(colors=max(colors * 2, 8), method=Image.MEDIANCUT,
                         dither=Image.Dither.NONE)
    pal = q.getpalette()
    counts = q.getcolors(size * size * used) or []
    total = sum(c for c, _ in counts) or 1
    ranked = sorted(counts, reverse=True)

    merged = []
    for count, idx in ranked:
        rgb = pal[idx * 3:idx * 3 + 3]
        if any(dist(rgb, m["rgb"]) < 900 for m in merged):   # ~30/channel
            continue
        merged.append({"hex": hexof(rgb), "rgb": rgb,
                       "pct": round(count / total, 4)})
        if len(merged) >= colors:
            break
    return merged


# ---- front matter injection -----------------------------------------------
def inject_palette(slug, hexes):
    path = os.path.join(AESTHETICS_DIR, slug + ".md")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    if not lines or lines[0].strip() != "---":
        return False
    try:
        close = lines.index("---", 1)
    except ValueError:
        return False
    body = [ln for ln in lines[1:close] if not ln.startswith("palette:")]
    palette_line = "palette: [%s]" % ", ".join('"%s"' % h for h in hexes)
    # place palette right after key_colours if present, else before source_url
    insert_at = len(body)
    for i, ln in enumerate(body):
        if ln.startswith("key_colours:"):
            insert_at = i + 1
            break
    else:
        for i, ln in enumerate(body):
            if ln.startswith("source_url:"):
                insert_at = i
                break
    body.insert(insert_at, palette_line)
    new = ["---"] + body + lines[close:]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(new))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--colors", type=int, default=6)
    ap.add_argument("--images-per", type=int, default=6)
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--no-inject", action="store_true")
    args = ap.parse_args()

    if args.slug:
        slugs = [args.slug]
    else:
        slugs = sorted(d for d in os.listdir(IMAGES_DIR)
                       if os.path.isdir(os.path.join(IMAGES_DIR, d)))
    if args.limit:
        slugs = slugs[:args.limit]

    palettes = {}
    if os.path.exists(os.path.join(DATA_DIR, "palettes.json")):
        with open(os.path.join(DATA_DIR, "palettes.json"), encoding="utf-8") as f:
            palettes = json.load(f)

    done, skipped, injected = 0, 0, 0
    for i, slug in enumerate(slugs, 1):
        paths = image_paths(slug, args.images_per)
        if not paths:
            skipped += 1
            continue
        cols = extract_palette(paths, args.colors, args.size)
        if not cols:
            skipped += 1
            continue
        palettes[slug] = {
            "colors": [{"hex": c["hex"], "pct": c["pct"]} for c in cols],
            "from_images": len(paths),
        }
        done += 1
        if not args.no_inject:
            if inject_palette(slug, [c["hex"] for c in cols]):
                injected += 1
        if i % 100 == 0:
            print("  %d/%d  ok=%d skipped=%d" % (i, len(slugs), done, skipped),
                  flush=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "palettes.json"), "w", encoding="utf-8") as f:
        json.dump(dict(sorted(palettes.items())), f, indent=2, ensure_ascii=False)

    print("\npalettes: %d  skipped(no images): %d  injected: %d"
          % (done, skipped, injected))


if __name__ == "__main__":
    main()
