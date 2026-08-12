#!/usr/bin/env python3
"""Merge per-page Figma PDF exports into one ebook PDF."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pypdf import PdfWriter


def merge(manifest_path: Path, pages_dir: Path, out_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    order = manifest["order"]
    writer = PdfWriter()
    missing: list[str] = []
    for i, item in enumerate(order):
        if item["kind"] == "cover":
            fname = "000-cover.pdf"
        else:
            fname = f"{item['n']:03d}-{item['name']}.pdf"
        path = pages_dir / fname
        if not path.is_file():
            missing.append(fname)
            continue
        writer.append(str(path))
    if missing:
        raise SystemExit(
            f"Missing {len(missing)} page PDF(s), e.g. {missing[:5]}. "
            f"Export leaves from Figma into {pages_dir} first."
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as fh:
        writer.write(fh)
    print(f"merged={len(order)} pages -> {out_path} ({out_path.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/ebook-export-manifest.json"),
    )
    parser.add_argument(
        "--pages-dir",
        type=Path,
        default=Path("exports/ebook-pages"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("exports/歸源手鏡-ebook.pdf"),
    )
    args = parser.parse_args()
    merge(args.manifest, args.pages_dir, args.out)


if __name__ == "__main__":
    main()
