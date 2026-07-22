# Attribution

This project is a derivative of the **Aesthetics Wiki**, a community wiki hosted
on Fandom.

- Source: https://aesthetics.fandom.com/wiki/Aesthetics_Wiki
- License of source text: CC-BY-SA 4.0 (https://www.fandom.com/licensing)
- Data retrieved via the MediaWiki API in July 2026.

Every entry under `aesthetics/` includes a `source_url` in its front matter and
a "Source and attribution" footer pointing back to the specific wiki page it was
adapted from. The authors of each page are listed in that page's revision
history on the wiki.

This repository is **not affiliated with, endorsed by, or sponsored by** the
Aesthetics Wiki, its contributors, or Fandom, Inc. All trademarks and content
belong to their respective owners.

## What this repo adds

- Wikitext converted to clean, portable markdown.
- Infobox fields normalised into structured YAML front matter.
- A compact search index (`data/index.json`) and a lookup CLI.
- Skill instructions (`SKILL.md`) for use with Claude Code / the Claude Agent SDK.

These additions (the code) are MIT licensed; the underlying text remains
CC-BY-SA 4.0. See `LICENSE` and `LICENSE-CONTENT.md`.
