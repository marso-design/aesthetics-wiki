---
name: aesthetics-wiki
description: >-
  Comprehensive knowledge base of ~1,200 internet visual aesthetics (Cottagecore,
  Vaporwave, Dark Academia, Cybergoth, Weirdcore, Coquette, and many more), with
  structured data (colours, hex palettes, motifs, values, related aesthetics,
  subgenres, era, platforms) plus full descriptions and moodboard generation.
  Use whenever the user wants to identify, name, describe, compare, or combine an
  aesthetic or "vibe"; find aesthetics by colour palette, decade, mood, or motif;
  discover related or adjacent aesthetics; build a moodboard or style guide; or
  design/theme something (outfit, room, brand, playlist, website/UI, poster) in a
  specific aesthetic. Triggers on "aesthetic", "vibe", "moodboard", "core", "what's
  it called when...", or any named aesthetic.
license: Code MIT; content CC-BY-SA 4.0 (Aesthetics Wiki). See LICENSE and ATTRIBUTION.md.
---

# Aesthetics Wiki

A local, self-contained, queryable corpus of internet visual aesthetics. Each
aesthetic is one markdown file with structured frontmatter and a full
description. Everything needed is in this folder; nothing is fetched from the
web. Do not load the whole corpus. Use the lookup CLI to find the right
aesthetic, then read only that one file.

## Data layout

- `data/index.json` - one compact record per aesthetic (name, aka, decade,
  colours, palette, motifs, values, related, subgenres, platforms, summary).
  Large; query it with the CLI rather than reading it whole.
- `aesthetics/<slug>.md` - full entry. Frontmatter fields:
  `name, aka, decade_of_origin, creators, key_motifs, key_colours, palette,
  key_values, related_aesthetics, subgenres, primary_platform, related_media,
  source_url`. Body is the full description (history, fashion, media, etc.).
  `palette` is a list of hex colours derived from the aesthetic's reference
  imagery (ranked by coverage) - use it as the real, buildable colour basis;
  `key_colours` is the prose description of the palette.
- `data/palettes.json` - the same palettes with coverage percentages.

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
  `--find` on X's colours/motifs to surface cousins that are not cross-linked.
- **Moodboard / style guide** - read the entry and list `palette`, `key_motifs`,
  `key_values`, and `related_media`. For a shareable image, run
  `python scripts/make_moodboard.py <slug>` (palette + motifs, no API, no
  third-party photos). If the user has configured an image API in `.env` (see
  README), run `python scripts/gen_moodboard.py <slug>` for a photo-based
  moodboard instead; fall back to `make_moodboard.py` when no key is set.
- **"Style my <outfit/room/brand/playlist/website> as <aesthetic>"** - translate
  `key_motifs`, `key_values`, and the hex `palette` into concrete choices for that
  medium. For UI/web/brand work, use `palette` directly as design tokens (CSS
  variables, a Tailwind theme, etc.), pairing motifs/values into type, layout, and
  imagery direction. Cite the aesthetic and offer 1-2 related aesthetics to blend.
- **Combine two aesthetics** - read both entries, find shared and contrasting
  motifs/colours, and propose a coherent fusion; name the overlap if a subgenre
  already covers it.
- **An aesthetic that is not in the index** - say it is not in this knowledge
  base rather than guessing, then offer the closest matches from `--find`.

## Attribution (required when you reproduce content)

The descriptive text is adapted from the **Aesthetics Wiki**, licensed
**CC-BY-SA 4.0**. When you quote or closely paraphrase an entry in a user-facing
deliverable, credit the Aesthetics Wiki and link the entry's `source_url`. Your
own synthesis, recommendations, summaries, and generated moodboards do not need
attribution.
