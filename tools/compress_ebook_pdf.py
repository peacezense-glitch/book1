#!/usr/bin/env python3
"""Raster-compress a merged ebook PDF toward a target file size.

Figma exports are high-resolution image PDFs (~150 MB). For distribution we
re-render each page to color JPEG and rebuild a lightweight PDF sized for phones.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

import img2pdf
from PIL import Image


def raster_page(src: Path, page_num: int, *, dpi: int, tmp_dir: Path) -> Path:
    prefix = tmp_dir / f"p{page_num:03d}"
    cmd = [
        "pdftoppm",
        "-jpeg",
        "-r",
        str(dpi),
        "-f",
        str(page_num),
        "-l",
        str(page_num),
        str(src),
        str(prefix),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    matches = sorted(tmp_dir.glob(f"p{page_num:03d}-*.jpg"))
    if not matches:
        raise FileNotFoundError(f"pdftoppm produced no JPEG for page {page_num}")
    return matches[0]


def jpeg_bytes(im: Image.Image, quality: int) -> bytes:
    bio = BytesIO()
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    elif im.mode == "L":
        im = im.convert("RGB")
    im.save(bio, format="JPEG", quality=quality, optimize=True)
    return bio.getvalue()


def compress(
    src: Path,
    out: Path,
    *,
    page_count: int,
    dpi: int,
    quality: int,
) -> tuple[int, int]:
    trim_w_mm = 152.0
    trim_h_mm = 230.0
    layout = img2pdf.get_layout_fun(
        (img2pdf.mm_to_pt(trim_w_mm), img2pdf.mm_to_pt(trim_h_mm))
    )

    with tempfile.TemporaryDirectory(prefix="ebook-compress-") as tmp:
        tmp_dir = Path(tmp)
        jpeg_paths: list[Path] = []
        total_jpeg = 0
        for n in range(1, page_count + 1):
            raw = raster_page(src, n, dpi=dpi, tmp_dir=tmp_dir)
            im = Image.open(raw)
            data = jpeg_bytes(im, quality)
            total_jpeg += len(data)
            out_jpg = tmp_dir / f"leaf-{n:03d}.jpg"
            out_jpg.write_bytes(data)
            jpeg_paths.append(out_jpg)
            raw.unlink(missing_ok=True)

        out.parent.mkdir(parents=True, exist_ok=True)
        pdf_bytes = img2pdf.convert(
            *[str(p) for p in jpeg_paths],
            layout_fun=layout,
        )
        out.write_bytes(pdf_bytes)

    return out.stat().st_size, total_jpeg


def pick_settings(target_bytes: int) -> tuple[int, int]:
    """Return dpi, jpeg quality for all-color output near target size."""
    # Color JPEG is ~2–3× heavier than gray at the same dpi/quality.
    presets = [
        (84, 22),
        (72, 28),
        (72, 22),
        (72, 18),
        (66, 16),
        (60, 15),
    ]
    for dpi, q in presets:
        _ = target_bytes
        return dpi, q
    return 72, 18


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in",
        dest="inp",
        type=Path,
        default=Path("exports/歸源手鏡-ebook.pdf"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("exports/歸源手鏡-ebook-5mb.pdf"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/ebook-export-manifest.json"),
    )
    parser.add_argument("--target-mb", type=float, default=5.0)
    parser.add_argument("--dpi", type=int, default=0)
    parser.add_argument("--quality", type=int, default=0, help="Color JPEG quality (1–95)")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    page_count = len(manifest["order"])
    target_bytes = int(args.target_mb * 1024 * 1024)

    dpi, quality = pick_settings(target_bytes)
    if args.dpi:
        dpi = args.dpi
    if args.quality:
        quality = args.quality

    for _ in range(5):
        size, jpeg_total = compress(
            args.inp,
            args.out,
            page_count=page_count,
            dpi=dpi,
            quality=quality,
        )
        if size <= target_bytes * 1.02:
            break
        quality = max(10, quality - 3)
        dpi = max(54, dpi - 6)

    mb = size / (1024 * 1024)
    print(
        f"compressed={page_count} pages color_jpeg dpi={dpi} quality={quality} "
        f"jpeg_total={jpeg_total/1e6:.2f}MB pdf={args.out} ({mb:.2f} MB, {size} bytes)"
    )
    if size > target_bytes * 1.05:
        raise SystemExit(
            f"Could not reach target {args.target_mb} MB (got {mb:.2f} MB). "
            "Lower --dpi or --quality manually."
        )


if __name__ == "__main__":
    main()
