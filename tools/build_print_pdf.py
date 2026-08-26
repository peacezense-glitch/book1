#!/usr/bin/env python3
"""Build a print PDF with bleed + CMYK from trim-size page PDFs.

Trim: 152 × 230 mm. Bleed: 3 mm each side → media 158 × 236 mm.
- Full-bleed leaves (cover / promo / plates): scale trim content to fill media.
- Other leaves: center trim on media (white 3 mm bleed).
Then convert RGB → CMYK via Ghostscript.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject

MM = 72 / 25.4
TRIM_W = 152 * MM
TRIM_H = 230 * MM
BLEED_MM = 3
MEDIA_W = (152 + BLEED_MM * 2) * MM
MEDIA_H = (230 + BLEED_MM * 2) * MM
BLEED_PT = BLEED_MM * MM

# Pages that should print edge-to-edge into bleed.
DEFAULT_FULL_BLEED = {"cover", "P005", "P228", "P293", "P317"}


def page_filename(item: dict) -> str:
    if item["kind"] == "cover":
        return "000-cover.pdf"
    return f"{item['n']:03d}-{item['name']}.pdf"


def place_on_bleed(src_page, full_bleed: bool):
    media = PageObject.create_blank_page(width=MEDIA_W, height=MEDIA_H)
    sw = float(src_page.mediabox.width)
    sh = float(src_page.mediabox.height)
    if full_bleed:
        sx = MEDIA_W / sw
        sy = MEDIA_H / sh
        # Uniform scale (cover aspect) — prefer fill.
        s = max(sx, sy)
        tx = (MEDIA_W - sw * s) / 2
        ty = (MEDIA_H - sh * s) / 2
        media.merge_transformed_page(
            src_page, Transformation().scale(s, s).translate(tx, ty)
        )
    else:
        # Fit trim into the trim box (centered with equal bleed).
        sx = TRIM_W / sw
        sy = TRIM_H / sh
        s = min(sx, sy)
        tx = BLEED_PT + (TRIM_W - sw * s) / 2
        ty = BLEED_PT + (TRIM_H - sh * s) / 2
        media.merge_transformed_page(
            src_page, Transformation().scale(s, s).translate(tx, ty)
        )
    # Box hints for print RIP (points).
    media.bleedbox = RectangleObject(media.mediabox)
    media.trimbox = RectangleObject(
        (BLEED_PT, BLEED_PT, BLEED_PT + TRIM_W, BLEED_PT + TRIM_H)
    )
    media.cropbox = RectangleObject(media.mediabox)
    return media


def build_bleed_rgb(manifest: dict, pages_dir: Path, out_rgb: Path, full_bleed: set[str]) -> int:
    writer = PdfWriter()
    missing: list[str] = []
    for item in manifest["order"]:
        fname = page_filename(item)
        path = pages_dir / fname
        if not path.is_file():
            missing.append(fname)
            continue
        reader = PdfReader(str(path))
        src = reader.pages[0]
        key = "cover" if item["kind"] == "cover" else item["name"]
        writer.add_page(place_on_bleed(src, key in full_bleed))
    if missing:
        raise SystemExit(f"Missing {len(missing)} page PDF(s), e.g. {missing[:5]}")
    out_rgb.parent.mkdir(parents=True, exist_ok=True)
    with out_rgb.open("wb") as fh:
        writer.write(fh)
    return len(writer.pages)


def rgb_to_cmyk(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "gs",
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dAutoRotatePages=/None",
        "-sColorConversionStrategy=CMYK",
        "-sProcessColorModel=DeviceCMYK",
        "-dConvertCMYKImagesToRGB=false",
        "-dEncodeColorImages=true",
        "-dEncodeGrayImages=true",
        f"-sOutputFile={dst}",
        str(src),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/ebook-export-manifest.json"))
    parser.add_argument("--pages-dir", type=Path, default=Path("exports/ebook-pages"))
    parser.add_argument("--out", type=Path, default=Path("exports/歸源手鏡-print-cmyk-bleed3mm.pdf"))
    parser.add_argument("--out-rgb", type=Path, default=Path("exports/歸源手鏡-print-rgb-bleed3mm.pdf"))
    parser.add_argument(
        "--full-bleed",
        default=",".join(sorted(DEFAULT_FULL_BLEED)),
        help="Comma-separated page names that fill the bleed (cover,P317,…)",
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    full_bleed = {x.strip() for x in args.full_bleed.split(",") if x.strip()}
    n = build_bleed_rgb(manifest, args.pages_dir, args.out_rgb, full_bleed)
    print(f"bleed-rgb pages={n} -> {args.out_rgb} ({args.out_rgb.stat().st_size} bytes)")
    rgb_to_cmyk(args.out_rgb, args.out)
    print(f"cmyk -> {args.out} ({args.out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
