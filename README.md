<div align="center">

# Aesthetics Wiki Skill

**A Claude skill that gives Claude a local, queryable knowledge base of 1,201 internet visual aesthetics.**

Cottagecore · Vaporwave · Dark Academia · Cybergoth · Weirdcore · Coquette · Mallsoft · and ~1,195 more.

![Claude Skill](https://img.shields.io/badge/Claude-Skill-8A2BE2)
![Aesthetics](https://img.shields.io/badge/aesthetics-1%2C201-ff69b4)
![Code](https://img.shields.io/badge/code-MIT-blue)
![Content](https://img.shields.io/badge/content-CC--BY--SA%204.0-lightgrey)

</div>

---

Ask Claude to name a vibe, build a moodboard, compare two aesthetics, or theme an
outfit / room / brand / playlist / UI, and this skill backs the answer with real,
structured reference data instead of guesswork. Adapted from the
[Aesthetics Wiki](https://aesthetics.fandom.com/wiki/Aesthetics_Wiki) via the
MediaWiki API, cleaned into portable markdown, and indexed for fast lookup.

## What Claude can do with it

- **Name it** - identify an aesthetic from a vague description ("what's it called when...").
- **Explain it** - origin, motifs, colours, values, related aesthetics.
- **Search it** - by colour palette, decade, mood, or motif.
- **Connect it** - surface related and adjacent aesthetics.
- **Build with it** - moodboards, style guides, or theme an outfit, room, brand, or website.
- **Blend it** - fuse two aesthetics into a coherent direction.

## At a glance

| | |
|---|---|
| Aesthetics | **1,201** |
| With structured palettes / relations | **1,125** |
| Reference images catalogued | **13,464** |
| Text size | ~18 MB |
| Source | Aesthetics Wiki (CC-BY-SA 4.0) |

## Install as a skill

```bash
git clone https://github.com/marso-design/aesthetics-wiki ~/.claude/skills/aesthetics-wiki
```

It activates automatically when a request matches its description (see the front
matter in [`SKILL.md`](SKILL.md)). No manual step needed.

**Images are not shipped in the repo** (they are large and carry their own
licenses). The text, structured data, and per-image `credits.json` manifests are
all included. When Claude needs to *see* an aesthetic's images, it fetches just
those on demand:

```bash
python scripts/fetch_image.py cottagecore --limit 1   # or --all
```

To bulk-populate every image locally instead, run `python scripts/scrape.py`.

## Usage examples

```console
$ python scripts/lookup.py "what's it called: nostalgic 90s shopping mall muzak"
Mallsoft   aesthetics/mallsoft.md
  decade_of_origin: 2010s
  key_colours: muted pastels, fluorescent lighting, washed-out tones
  Mallsoft is a subgenre of vaporwave evoking the ambience of empty shopping malls...

$ python scripts/lookup.py --related Cottagecore
Fairycore, Goblincore, Grandmacore, Naturecore, Mori Kei, Bloomcore, Cottagegoth ...

$ python scripts/lookup.py --color pastel --limit 5
$ python scripts/lookup.py --decade 1990s
$ python scripts/lookup.py --get "dark academia"
```

Add `--json` for structured output, `--limit N` to widen results.

## What's in each entry

Every `aesthetics/<slug>.md` has structured front matter plus the full description:

```yaml
name: "Cottagecore"
aka: ["Farmcore", "Countrycore"]
decade_of_origin: "2010s (inspired by the 19th century)"
key_motifs: ["Baking", "gardening", "foraging", "picnics", "wildflowers", ...]
key_colours: ["Earthy and natural tones (brown, moss green, beige)", "soft pastels", ...]
key_values: ["Simplicity", "self-sufficiency", "harmony with nature", ...]
related_aesthetics: ["Fairycore", "Goblincore", "Grandmacore", ...]
subgenres: ["Bloomcore", "Cottagegoth", "Gardencore", ...]
primary_platform: ["Tumblr", "TikTok"]
source_url: "https://aesthetics.fandom.com/wiki/Cottagecore"
```

## How it works

- **Sourced via the MediaWiki API**, not HTML scraping. Polite by design
  (descriptive User-Agent, `maxlag`, retry-with-backoff) and resumable.
- **Infobox parsing** normalises each `{{Aesthetic}}` template into typed front matter.
- **Progressive disclosure**: the skill queries a compact index and reads one
  entry at a time, so it stays fast at 1,200+ pages instead of loading everything.

## Repository layout

```
SKILL.md               # skill definition + the lookup protocol Claude follows
aesthetics/<slug>.md   # 1,201 entries: structured front matter + full text
images/<slug>/         # credits.json manifests (binaries fetched on demand)
data/index.json        # compact search index
scripts/scrape.py      # pull everything from the wiki (resumable)
scripts/build_index.py # rebuild data/index.json from the files
scripts/lookup.py      # query CLI (resolve, search, related, by colour/decade/motif)
scripts/fetch_image.py # fetch an aesthetic's images on demand for local viewing
```

## Regenerate from source

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python scripts/scrape.py            # full pull (text + images), resumable
python scripts/build_index.py       # rebuild the search index
python scripts/lookup.py --stats    # sanity check
```

## Licensing

- **Code** (`scripts/`, `SKILL.md`): MIT. See [`LICENSE`](LICENSE).
- **Text** (`aesthetics/`): CC-BY-SA 4.0, from the Aesthetics Wiki. Attribute and
  share-alike. See [`LICENSE-CONTENT.md`](LICENSE-CONTENT.md) and [`ATTRIBUTION.md`](ATTRIBUTION.md).
- **Images**: each carries its own, often unspecified, license. They are excluded
  from this repo by default; only the `credits.json` manifests are tracked. Verify
  a given image's license before republishing it.

Not affiliated with, endorsed by, or sponsored by the Aesthetics Wiki or Fandom, Inc.

---

<div align="center">

Built by **[Marso Design](https://github.com/marso-design)** - brand, site, and product UI, shipped.

</div>
