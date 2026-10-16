"""Build the app's UI font "HRMS Sans": Noto Sans (Latin) and Noto Sans Khmer merged into one family.

Tk draws a label with a single font. When that font lacks a letter, Windows picks some other font for
it, so Latin text set in a Khmer-only font (or Khmer text set in Segoe UI) comes out in a mismatched
style. One family that holds both scripts, designed to match, looks right in both languages and
for mixed text such as a Khmer name on an English screen.

    pip install fonttools ttfautohint-py
    python scripts/build_fonts.py

Downloads the sources, merges each weight, re-hints the result (ttfautohint, Latin + Khmer) and
writes frontend/assets/fonts/HRMSSans-*.ttf. Only needed when the fonts should be rebuilt.
"""
import io
import sys
import tempfile
import urllib.request
from pathlib import Path

import ttfautohint
from fontTools import subset
from fontTools.merge import Merger
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "frontend" / "assets" / "fonts"
SOURCE = "https://github.com/notofonts/notofonts.github.io/raw/main/fonts/{family}/unhinted/ttf/{family}-{weight}.ttf"
WEIGHTS = ("Regular", "SemiBold", "Bold")
FAMILY = "HRMS Sans"

# Latin, Latin-1, punctuation, currency, arrows and a few symbols; the rest of Noto Sans
# (Greek, Cyrillic, Vietnamese, ...) is dropped to keep the files small.
LATIN = "U+0000-024F,U+02B0-02FF,U+0300-036F,U+1E00-1EFF,U+2000-206F,U+20A0-20CF,U+2100-214F,U+2190-21FF," \
        "U+2200-22FF,U+25A0-25FF,U+2700-27BF,U+FEFF"


def download(family: str, weight: str, folder: Path) -> Path:
    path = folder / f"{family}-{weight}.ttf"
    with urllib.request.urlopen(SOURCE.format(family=family, weight=weight)) as response:
        path.write_bytes(response.read())
    return path


def unhinted(path: Path, unicodes: str | None, out: Path) -> Path:
    """Copy of the font without hinting (merging needs that), limited to `unicodes` (None: keep all)."""
    options = subset.Options()
    options.hinting = False
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.glyph_names = True
    font = TTFont(path)
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=font.getBestCmap() if unicodes is None else subset.parse_unicodes(unicodes))
    subsetter.subset(font)
    font.save(out)
    return out


def rename(font: TTFont, weight: str) -> None:
    """Give the merged font its own name, so it never clashes with an installed Noto Sans."""
    ps_name = f"HRMSSans-{weight}"
    legacy_family = FAMILY if weight in ("Regular", "Bold") else f"{FAMILY} {weight}"
    legacy_style = weight if weight in ("Regular", "Bold") else "Regular"
    name = font["name"]
    copyright_ = name.getDebugName(0)
    name.names = []
    for name_id, value in {
        0: f"{copyright_}. Khmer glyphs: Copyright 2022 The Noto Project Authors (https://github.com/notofonts/khmer)",
        1: legacy_family,
        2: legacy_style,
        3: f"{ps_name};G5_E_HRMS",
        4: f"{FAMILY} {weight}",
        5: "Version 1.000; Noto Sans + Noto Sans Khmer",
        6: ps_name,
        10: "Noto Sans and Noto Sans Khmer merged for the G5_E_HRMS desktop app.",
        13: "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
        14: "https://openfontlicense.org",
        16: FAMILY,
        17: weight,
    }.items():
        name.setName(value, name_id, 3, 1, 0x409)  # Windows, Unicode BMP, English (US)


def build(weight: str, folder: Path) -> Path:
    latin = unhinted(download("NotoSans", weight, folder), LATIN, folder / f"latin-{weight}.ttf")
    khmer = unhinted(download("NotoSansKhmer", weight, folder), None, folder / f"khmer-{weight}.ttf")

    # Latin first: its digits and punctuation win where both fonts have them.
    merged = Merger().merge([str(latin), str(khmer)])
    a, b = TTFont(latin), TTFont(khmer)
    os2 = merged["OS/2"]
    # Khmer stacks need the taller Khmer line height, also on English screens.
    os2.usWinAscent = max(a["OS/2"].usWinAscent, b["OS/2"].usWinAscent)
    os2.usWinDescent = max(a["OS/2"].usWinDescent, b["OS/2"].usWinDescent)
    os2.ulCodePageRange1 |= b["OS/2"].ulCodePageRange1
    rename(merged, weight)

    buffer = io.BytesIO()
    merged.save(buffer)
    hinted = ttfautohint.ttfautohint(in_buffer=buffer.getvalue(), fallback_script="latn",
                                     windows_compatibility=True, no_info=True)
    out = OUT_DIR / f"HRMSSans-{weight}.ttf"
    out.write_bytes(hinted)
    return out


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for weight in WEIGHTS:
            print("built", build(weight, Path(tmp)).relative_to(ROOT))


if __name__ == "__main__":
    sys.exit(main())
