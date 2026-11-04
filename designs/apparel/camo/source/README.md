# Owner base camo: source master

Put the owner's original SVG here as **`owner_base.svg`**, byte-exact.
Upload it on GitHub: open this folder → Add file → Upload files.

Palette taken from the SVG:
| Role | Hex |
|---|---|
| Base / field (tan) | #ae9d6c |
| Olive | #8b8148 |
| Light tan (highlight) | #c6b497 |
| Dark (shadow) | #313120 |

## What happens when the file arrives
`huntkit.camo.owner_base.load_owner_base()` checks for `owner_base.svg` here. If it is present
it is used automatically (cairosvg rasteriser if installed, else the pure-Python even-odd
scanline filler); if not, a procedural **PROXY** is used and every preview says "PROXY".
**Status 2026-11-04:** the file is here and ingested. `../owner_base.yaml › measured` and the
Owner Base section of `../DESIGN.md` hold the real measurements. If the art changes, re-run
`python -m huntkit.camo.cli owner-base` and update both.
