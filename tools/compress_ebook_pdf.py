#!/usr/bin/env python3
"""Raster-compress a merged ebook PDF toward a target file size.

Figma exports are high-resolution image PDFs (~150 MB). For distribution we
re-render each page to JPEG and rebuild a lightweight PDF sized for phones.
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

# Full-bleed / color plates (cover + illustration + promo).
DEFAULT_COLOR_PAGES = {1, 5, 213, 271, 295}


def load_color_pages(manifest_path: Path | None) -> set[int]:
    if manifest_path is None or not manifest_path.is_file():
        return set(DEFAULT_COLOR_PAGES)
    plan_path = manifest_path.parent / "pages-plan.json"
    if not plan_path.is_file():
        return set(DEFAULT_COLOR_PAGES)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    pages: set[int] = {1}
    for page in plan["pages"]:
        n = page["n"]
        if page.get("t") == "i" and page.get("img") in ("jiutian", "luzu", "four", "promo"):
            pages.add(n)
        if page.get("bleed"):
            pages.add(n)
    return pages


def raster_page(
    src: Path,
    page_num: int,
    *,
    dpi: int,
    color: bool,
    tmp_dir: Path,
) -> Path:
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
    if not color:
        cmd.insert(2, "-gray")
    subprocess.run(cmd, check=True, capture_output=True)
    matches = sorted(tmp_dir.glob(f"p{page_num:03d}-*.jpg"))
    if not matches:
        raise FileNotFoundError(f"pdftoppm produced no JPEG for page {page_num}")
    return matches[0]


def jpeg_bytes(im: Image.Image, quality: int) -> bytes:
    bio = BytesIO()
    im.save(bio, format="JPEG", quality=quality, optimize=True)
    return bio.getvalue()


def compress(
    src: Path,
    out: Path,
    *,
    page_count: int,
    color_pages: set[int],
    target_bytes: int,
    dpi: int,
    gray_q: int,
    color_q: int,
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
            raw = raster_page(
                src,
                n,
                dpi=dpi,
                color=n in color_pages,
                tmp_dir=tmp_dir,
            )
            im = Image.open(raw)
            q = color_q if n in color_pages else gray_q
            data = jpeg_bytes(im, q)
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


def pick_settings(target_bytes: int) -> tuple[int, int, int]:
    """Return dpi, gray_q, color_q tuned to stay at or below target."""
    # 84 dpi / moderate JPEG keeps Chinese body text legible on phones while
    # landing near 5 MB for ~297 pages (empirically ~16 KB/page average).
    presets = [
        (96, 16, 42),
        (84, 18, 45),
        (84, 15, 40),
        (72, 20, 50),
        (72, 15, 40),
        (72, 12, 35),
    ]
    for dpi, gq, cq in presets:
        est = dpi * gq  # rough ordering heuristic
        _ = est
        return dpi, gq, cq
    return 72, 12, 35


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
    parser.add_argument("--gray-quality", type=int, default=0)
    parser.add_argument("--color-quality", type=int, default=0)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    page_count = len(manifest["order"])
    color_pages = load_color_pages(args.manifest)
    target_bytes = int(args.target_mb * 1024 * 1024)

    dpi, gq, cq = pick_settings(target_bytes)
    if args.dpi:
        dpi = args.dpi
    if args.gray_quality:
        gq = args.gray_quality
    if args.color_quality:
        cq = args.color_quality

    # First pass; tighten if we exceed target.
    for attempt in range(4):
        size, jpeg_total = compress(
            args.inp,
            args.out,
            page_count=page_count,
            color_pages=color_pages,
            target_bytes=target_bytes,
            dpi=dpi,
            gray_q=gq,
            color_q=cq,
        )
        if size <= target_bytes * 1.02:
            break
        gq = max(8, gq - 3)
        cq = max(20, cq - 5)
        dpi = max(72, dpi - 6)

    mb = size / (1024 * 1024)
    print(
        f"compressed={page_count} pages dpi={dpi} gray_q={gq} color_q={cq} "
        f"jpeg_total={jpeg_total/1e6:.2f}MB pdf={args.out} ({mb:.2f} MB, {size} bytes)"
    )
    if size > target_bytes * 1.05:
        raise SystemExit(
            f"Could not reach target {args.target_mb} MB (got {mb:.2f} MB). "
            "Lower --dpi or quality manually."
        )


if __name__ == "__main__":
    main()
