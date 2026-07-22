---
name: aesthetics-wiki
description: >-
  Comprehensive knowledge base of ~1,200 internet visual aesthetics (Cottagecore,
  Vaporwave, Dark Academia, Cybergoth, Weirdcore, Coquette, and many more), scraped
  from the Aesthetics Wiki with structured data (colours, motifs, values, related
  aesthetics, subgenres, era, platforms) plus full descriptions and reference images.
  Use whenever the user wants to identify, name, describe, compare, or combine an
  aesthetic or "vibe"; find aesthetics by colour palette, decade, mood, or motif;
  discover related or adjacent aesthetics; build a moodboard or style guide; or
  design/theme something (outfit, room, brand, playlist, website/UI, poster) in a
  specific aesthetic. Triggers on "aesthetic", "vibe", "moodboard", "core", "what's
  it called when...", or any named aesthetic.
license: Code MIT; content CC-BY-SA 4.0 (Aesthetics Wiki). See LICENSE and ATTRIBUTION.md.
---

# Aesthetics Wiki

A local, queryable corpus of internet visual aesthetics. Each aesthetic is one
markdown file with structured frontmatter and a full description; reference
images sit under `images/<slug>/`. Do not load the whole corpus. Use the lookup
CLI to find the right aesthetic, then read only that one file.

## Data layout

- `data/index.json` - one compact record per aesthetic (name, aka, decade,
  colours, motifs, values, related, subgenres, platforms, summary, image count).
  Large; query it with the CLI rather than reading it whole.
- `aesthetics/<slug>.md` - full entry. Frontmatter fields:
  `name, aka, decade_of_origin, creators, key_motifs, key_colours, palette,
  key_values, related_aesthetics, subgenres, primary_platform, related_media,
  source_url, image_count`. Body is the full description (history, fashion, etc.).
  `palette` is a list of hex colours **derived from the aesthetic's actual
  reference images** (ranked by coverage) - use it as the real, buildable colour
  basis; `key_colours` is the wiki's prose description of the palette.
- `images/<slug>/` - reference images + `credits.json` (per-image source URL,
  uploader, license where the wiki recorded one). The `credits.json` manifest is
  always present; the image binaries may or may not be downloaded locally (they
  are excluded from the published repo, see "Viewing images" below).

## Lookup CLI (use this first)

Run from the skill root. Prefer it over grepping raw JSON.

```bash
python scripts/lookup.py "dark academia"     # smart: resolves a name, else searches
python scripts/lookup.py --get cottagecore   # one entry, verbose, with its file path
python scripts/lookup.py --find "green forest witch"   # full-text across all fields
python scripts/lookup.py --color pastel      # aesthetics whose palette matches
python scripts/lookup.py --decade 1990s      # aesthetics of an era
python scripts/lookup.py --motif mushroom    # aesthetics sharing a motif
python scripts/lookup.py --related Cottagecore   # its related aesthetics + subgenres
python scripts/lookup.py --list              # every slug + name
python scripts/lookup.py --stats             # coverage counts
```

Add `--json` for structured output, `--limit N` to widen results.

After the CLI points you to a file, read `aesthetics/<slug>.md` for the depth
(history, fashion, music, decor, values) you need to answer well.

## How to handle common requests

- **"What aesthetic is this / what's it called when..."** - pull the distinctive
  cues (colours, era, objects, mood) from the user, run `--find` with them, and
  present the top 2-3 candidates with a one-line contrast. Confirm with the user
  before committing to one.
- **"Describe / explain <aesthetic>"** - `--get <name>`, then read the file and
  summarise its origin, key motifs, colours, values, and related aesthetics.
- **"Show me aesthetics like X" / adjacent vibes** - `--related X`, and also
  `--find` on X's colours/motifs to surface cousins the wiki did not cross-link.
- **Moodboard / style guide** - read the entry, list `key_colours`, `key_motifs`,
  `related_media`, and reference specific files from `images/<slug>/`. Note the
  image licensing caveat below before reusing any image externally. For a
  shareable visual moodboard, run `python scripts/make_moodboard.py <slug>` - it
  renders the palette + motifs into an image with no third-party photos.
- **"Style my <outfit/room/brand/playlist/website> as <aesthetic>"** - translate
  `key_motifs`, `key_values`, and the hex `palette` into concrete choices for that
  medium. For UI/web/brand work, use `palette` directly as design tokens (CSS
  variables, a Tailwind theme, etc.), pairing motifs/values into type, layout, and
  imagery direction. Cite the aesthetic and offer 1-2 related aesthetics to blend.
- **Combine two aesthetics** - read both entries, find shared and contrasting
  motifs/colours, and propose a coherent fusion; name the overlap if the wiki has
  a subgenre for it.

## Viewing images

Images are for **visual reference** (letting you actually see an aesthetic), not
for republishing. To view them:

1. If `images/<slug>/<file>` exists locally, `Read` it directly.
2. If the binary is not present (fresh install, binaries excluded from the repo),
   fetch just what you need on demand, then `Read` the printed path:

   ```bash
   python scripts/fetch_image.py cottagecore --limit 1   # cover image only
   python scripts/fetch_image.py cottagecore --name book # images matching "book"
   python scripts/fetch_image.py cottagecore --all       # every image for it
   ```

Fetch only the handful of images relevant to the task. Do not republish or embed
these images in an external deliverable without checking each one's license in
`credits.json`.

## Attribution (required when you reproduce content)

The descriptive text is from the **Aesthetics Wiki** (aesthetics.fandom.com),
licensed **CC-BY-SA 4.0**. When you quote or closely paraphrase an entry in a
user-facing deliverable, credit the Aesthetics Wiki and link the entry's
`source_url`. Your own synthesis, recommendations, and summaries do not need
attribution.

**Images are not uniformly licensed.** Each file in `images/<slug>/` carries its
own (often unspecified) license, recorded in that folder's `credits.json`. Treat
them as references for internal moodboarding. Do not republish an image
externally without checking its individual license first.

## Regenerating the data

`python scripts/scrape.py` re-pulls from the wiki; `python scripts/build_index.py`
rebuilds `data/index.json` from the files. See README.md.
