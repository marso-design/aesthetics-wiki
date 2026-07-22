"""
Generate a moodboard image for an aesthetic from data we own: its derived
palette plus its motifs / decade / platform. No third-party photos, so it is
free of image-licensing issues while still reading like a moodboard.

    python scripts/make_moodboard.py cottagecore
    python scripts/make_moodboard.py vaporwave --out assets/moodboards/vaporwave.png
    python scripts/make_moodboard.py --all --limit 30
"""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

FONT_CANDIDATES = {
    "display": [("/System/Library/Fonts/Supplemental/Futura.ttc", 0)],
    "text": [("/System/Library/Fonts/HelveticaNeue.ttc", 0),
             ("/System/Library/Fonts/Supplemental/Arial.ttf", 0)],
}

# tiles (of a 5x3 grid) that hold a motif keyword instead of a pure colour
KEYWORD_TILES = [2, 6, 9, 13]
GRAD_EVERY = 3


def load_font(kind, size):
    for path, idx in FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(path, size=size, index=idx)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def luminance(rgb):
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255


def ink_for(bg):
    return (20, 20, 26) if luminance(bg) > 0.6 else (240, 240, 244)


def rounded(tile, radius):
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.size[0] - 1,
                                            tile.size[1] - 1], radius=radius,
                                           fill=255)
    tile.putalpha(mask)
    return tile


def color_tile(w, h, c1, c2=None, radius=12):
    tile = Image.new("RGBA", (w, h), c1 + (255,))
    if c2 is not None:
        d = ImageDraw.Draw(tile)
        for y in range(h):
            d.line([(0, y), (w, y)], fill=lerp(c1, c2, y / max(h - 1, 1)) + (255,))
    return rounded(tile, radius)


def fit_font(draw, text, kind, max_w, start=34, floor=16):
    size = start
    while size > floor:
        f = load_font(kind, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return load_font(kind, floor)


def tracked(draw, xy, text, font, fill, spacing):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def build(slug, palettes, meta, out):
    pal = [c["hex"] for c in palettes[slug]["colors"][:6]]
    rgb = [hex2rgb(h) for h in pal]
    m = meta.get(slug, {})
    name = m.get("name", slug)
    motifs = [w for w in m.get("key_motifs", []) if 3 <= len(w) <= 18][:4]
    meta_bits = [b for b in [m.get("decade_of_origin"),
                 (m.get("primary_platform") or [None])[0]] if b]

    W = 1200
    margin, gap = 48, 16
    header_h, footer_h = 190, 78
    cols, rows = 5, 3
    grid_w = W - 2 * margin
    tile_w = (grid_w - (cols - 1) * gap) // cols
    tile_h = 150
    grid_h = rows * tile_h + (rows - 1) * gap
    H = header_h + grid_h + footer_h + margin

    img = Image.new("RGB", (W, H), (13, 13, 17))
    d = ImageDraw.Draw(img)

    # header
    f_name = fit_font(d, name.upper(), "display", grid_w - 20, start=84, floor=40)
    tracked(d, (margin, margin), name.upper(), f_name, (243, 243, 246), 5)
    if meta_bits:
        d.text((margin + 3, header_h - 42), "   .   ".join(meta_bits),
               font=load_font("text", 24), fill=(150, 150, 165))

    # grid
    ki = 0
    y0 = header_h
    for i in range(cols * rows):
        r, c = divmod(i, cols)
        x = margin + c * (tile_w + gap)
        y = y0 + r * (tile_h + gap)
        base = rgb[i % len(rgb)]
        if i in KEYWORD_TILES and ki < len(motifs):
            tile = color_tile(tile_w, tile_h, base)
            img.paste(tile, (x, y), tile)
            word = motifs[ki].lower()
            ki += 1
            f = fit_font(d, word, "text", tile_w - 28, start=30, floor=15)
            tw = d.textlength(word, font=f)
            d.text((x + (tile_w - tw) / 2, y + tile_h / 2 - f.size / 2),
                   word, font=f, fill=ink_for(base))
        else:
            c2 = rgb[(i + 2) % len(rgb)] if i % GRAD_EVERY == 0 else None
            tile = color_tile(tile_w, tile_h, base, c2)
            img.paste(tile, (x, y), tile)

    # footer: palette hex row + brand
    fy = header_h + grid_h + 26
    d.line([(margin, fy - 8), (W - margin, fy - 8)], fill=(32, 32, 40), width=2)
    f_small = load_font("text", 20)
    x = margin
    for h in pal:
        sw = 22
        d.rounded_rectangle([x, fy + 6, x + sw, fy + 6 + sw], radius=5,
                            fill=hex2rgb(h))
        d.text((x + sw + 8, fy + 9), h, font=f_small, fill=(150, 150, 165))
        x += sw + 8 + d.textlength(h, font=f_small) + 16
    brand = "marso.design"
    d.text((W - margin - d.textlength(brand, font=f_small), fy + 9), brand,
           font=f_small, fill=(120, 120, 135))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, optimize=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    with open(os.path.join(DATA, "palettes.json"), encoding="utf-8") as f:
        palettes = json.load(f)
    with open(os.path.join(DATA, "index.json"), encoding="utf-8") as f:
        meta = {r["slug"]: r for r in json.load(f)}

    if args.all:
        slugs = [s for s in palettes]
        if args.limit:
            slugs = slugs[:args.limit]
    elif args.slug:
        if args.slug not in palettes:
            raise SystemExit("no palette for '%s' (needs local images + palette.py)"
                             % args.slug)
        slugs = [args.slug]
    else:
        raise SystemExit("give a slug or --all")

    for slug in slugs:
        out = args.out or os.path.join(ROOT, "assets", "moodboards", slug + ".png")
        build(slug, palettes, meta, out)
        print("wrote", out)


if __name__ == "__main__":
    main()
