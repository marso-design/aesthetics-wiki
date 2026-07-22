"""
Generate a moodboard IMAGE for an aesthetic with a text-to-image model, using
the aesthetic's own data (name, motifs, values, palette) as the prompt.

Bring your own provider. Configure via environment (.env is loaded if present):

    IMAGE_PROVIDER   gemini | openai        (default: gemini)
    IMAGE_MODEL      model id               (default: gemini-3.1-flash-image, aka "Nano Banana 2")
    IMAGE_API_KEY    your key               (or GEMINI_API_KEY / OPENAI_API_KEY)
    IMAGE_API_BASE   optional base URL override (for resellers / OpenRouter / proxies)

The key is read from the environment and NEVER printed or committed. Keep it in
.env (git-ignored). If no key is set, this script only prints the prompt; the
free fallback is scripts/make_moodboard.py (palette + motifs, no API).

    python scripts/gen_moodboard.py cottagecore --dry-run   # show prompt, no API call, no cost
    python scripts/gen_moodboard.py cottagecore             # generate one
    python scripts/gen_moodboard.py --all --limit 5         # small batch
"""

import argparse
import base64
import json
import os

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "assets", "generated")


def load_env():
    """Minimal .env loader (no dependency). Does not override existing env."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            v = v.strip()
            if v[:1] not in ('"', "'"):
                # strip an inline comment (a '#' preceded by whitespace or at start)
                for i, ch in enumerate(v):
                    if ch == "#" and (i == 0 or v[i - 1].isspace()):
                        v = v[:i]
                        break
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def build_prompt(slug, meta, palette):
    name = meta.get("name", slug)
    motifs = ", ".join(meta.get("key_motifs", [])[:8])
    values = ", ".join(meta.get("key_values", [])[:5])
    hexes = ", ".join(palette[:6])
    summary = (meta.get("summary") or "")[:240]
    parts = [
        "A moodboard collage capturing the '%s' aesthetic." % name,
        ("Themes and motifs: %s." % motifs) if motifs else "",
        ("Mood and values: %s." % values) if values else "",
        ("Colour palette (approximate): %s." % hexes) if hexes else "",
        summary,
        "Compose as a cohesive grid-style moodboard of atmospheric photographs, "
        "textures, and details in this aesthetic. Editorial, tasteful, high detail. "
        "No text, captions, watermarks, or logos. Do not depict real, identifiable "
        "people, brands, or copyrighted characters.",
    ]
    return " ".join(p for p in parts if p)


# ---- providers -------------------------------------------------------------
def gen_gemini(prompt, model, key, base):
    base = base or "https://generativelanguage.googleapis.com/v1beta"
    url = "%s/models/%s:generateContent" % (base.rstrip("/"), model)
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    # key goes in a header, never the URL, so it cannot leak into error messages
    r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=180)
    r.raise_for_status()
    data = r.json()
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    raise RuntimeError("no image in Gemini response: %s" % json.dumps(data)[:400])


def gen_openai(prompt, model, key, base, size="1024x1024"):
    base = base or "https://api.openai.com/v1"
    url = "%s/images/generations" % base.rstrip("/")
    body = {"model": model, "prompt": prompt, "size": size, "n": 1}
    r = requests.post(url, headers={"Authorization": "Bearer %s" % key},
                      json=body, timeout=180)
    r.raise_for_status()
    item = r.json()["data"][0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        img = requests.get(item["url"], timeout=180)
        img.raise_for_status()
        return img.content
    raise RuntimeError("no image in OpenAI response")


PROVIDERS = {"gemini": gen_gemini, "openai": gen_openai}


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--provider", default=os.environ.get("IMAGE_PROVIDER", "gemini"))
    ap.add_argument("--model", default=os.environ.get("IMAGE_MODEL",
                                                       "gemini-3.1-flash-image"))
    ap.add_argument("--base", default=os.environ.get("IMAGE_API_BASE"))
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the prompt only; no API call, no cost")
    args = ap.parse_args()

    with open(os.path.join(DATA, "palettes.json"), encoding="utf-8") as f:
        palettes = json.load(f)
    with open(os.path.join(DATA, "index.json"), encoding="utf-8") as f:
        meta = {r["slug"]: r for r in json.load(f)}

    if args.all:
        slugs = list(palettes)[:args.limit] if args.limit else list(palettes)
    elif args.slug:
        slugs = [args.slug]
    else:
        raise SystemExit("give a slug or --all")

    key = (os.environ.get("IMAGE_API_KEY")
           or os.environ.get("GEMINI_API_KEY")
           or os.environ.get("OPENAI_API_KEY"))
    gen = PROVIDERS.get(args.provider)
    if not gen:
        raise SystemExit("unknown provider '%s' (have: %s)"
                         % (args.provider, ", ".join(PROVIDERS)))

    os.makedirs(args.out_dir, exist_ok=True)
    for slug in slugs:
        pal = [c["hex"] for c in palettes.get(slug, {}).get("colors", [])]
        prompt = build_prompt(slug, meta.get(slug, {}), pal)
        if args.dry_run:
            print("\n=== %s ===\n%s" % (slug, prompt))
            continue
        if not key:
            raise SystemExit(
                "no API key found. Add IMAGE_API_KEY (or GEMINI_API_KEY) to .env, "
                "or use --dry-run. Free fallback: scripts/make_moodboard.py")
        try:
            img = gen(prompt, args.model, key, args.base)
            out = os.path.join(args.out_dir, slug + ".png")
            with open(out, "wb") as f:
                f.write(img)
            print("wrote", out)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).replace(key, "***") if key else str(exc)
            print("FAIL %s: %s" % (slug, msg))


if __name__ == "__main__":
    main()
