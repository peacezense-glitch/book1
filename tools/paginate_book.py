#!/usr/bin/env python3
"""Paginate《歸源手鏡》into vertical RTL page plan for Figma.

Binding: odd pages on the RIGHT, even pages on the LEFT (直排右翻).
Body metrics default to 10.5 pt / 14.7 lh / 15×32 grid.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
from pathlib import Path

ROWS = 32
COLS = 15
CAP = ROWS * COLS
TIP_RE = re.compile(r"^(本章實修功課|實戰練習|主功課|輔助功課|本週|今天的功課)")
VERTICAL_FORMS = {
    "「": "﹁",
    "」": "﹂",
    "『": "﹃",
    "』": "﹄",
    "（": "︵",
    "）": "︶",
    "【": "︻",
    "】": "︼",
    "《": "︽",
    "》": "︾",
    "〈": "︿",
    "〉": "﹀",
    "〔": "︹",
    "〕": "︺",
    "［": "﹇",
    "］": "﹈",
    "—": "︱",
    "─": "︱",
    "…": "︙",
}
STYLE = {
    "body": "0",
    "heading": "1",
    "subtitle": "2",
    "spacer": "3",
    "pad": "4",
}


def strip_spaces(text: str) -> str:
    return re.sub(r"[\u3000\s]+", "", text)


def vert(chars: list[str]) -> list[str]:
    return [VERTICAL_FORMS.get(ch, ch) for ch in chars]


def is_tip(text: str) -> bool:
    return bool(TIP_RE.match(strip_spaces(text)))


def build_items(book: dict) -> list[dict]:
    paragraphs = book["paragraphs"]
    items: list[dict] = []

    for paragraph in paragraphs:
        if paragraph["kind"] != "toc":
            break
        text = strip_spaces(paragraph["text"])
        if not text:
            continue
        kind = "toc_title" if ("總目錄" in text or text == "目錄") else "toc_item"
        items.append({"kind": kind, "text": text})

    start = next(i for i, p in enumerate(paragraphs) if p["kind"] != "toc")
    end = 2098  # before duplicate colophon dump in paragraphs
    for paragraph in paragraphs[start:end]:
        kind = paragraph["kind"]
        text = strip_spaces(paragraph["text"])
        if not text:
            continue
        if kind in ("volume", "chapter", "major"):
            items.append({"kind": "opener", "level": kind, "text": text})
        elif kind == "heading":
            items.append({"kind": "heading", "text": text})
        elif is_tip(paragraph["text"]):
            items.append({"kind": "subtitle", "text": text})
        else:
            items.append({"kind": "body", "text": text})

    items.append({"kind": "opener", "level": "chapter", "text": "版權頁"})
    for line in book.get("backMatter", []):
        text = strip_spaces(line if isinstance(line, str) else str(line))
        if text:
            items.append({"kind": "body", "text": text})
    return items


def paginate(items: list[dict]) -> list[dict]:
    pages: list[dict] = []
    buf: list[dict] = []

    def flush_full_pages() -> None:
        nonlocal buf
        while len(buf) >= CAP:
            pages.append({"type": "body", "cells": buf[:CAP]})
            buf = buf[CAP:]

    for item in items:
        kind = item["kind"]
        if kind == "opener":
            flush_full_pages()
            if buf:
                while len(buf) < CAP:
                    buf.append({"c": "", "s": "pad"})
                pages.append({"type": "body", "cells": buf})
                buf = []
            if len(pages) % 2 == 1:
                pages.append({"type": "blank"})
            pages.append(
                {
                    "type": "opener",
                    "level": item.get("level", "chapter"),
                    "text": item["text"],
                }
            )
            continue

        if kind in ("heading", "subtitle", "toc_title"):
            style = "subtitle" if kind == "subtitle" else "heading"
            chars = vert(list(item["text"]))
            need = len(chars) + ROWS
            in_page = len(buf) % CAP
            if in_page and (CAP - in_page) < need:
                while len(buf) % CAP:
                    buf.append({"c": "", "s": "pad"})
            for ch in chars:
                buf.append({"c": ch, "s": style})
            while len(buf) % ROWS:
                buf.append({"c": "", "s": "pad"})
            for _ in range(ROWS):
                buf.append({"c": "", "s": "spacer"})
        else:
            for ch in vert(list(item["text"])):
                buf.append({"c": ch, "s": "body"})
            while len(buf) % ROWS:
                buf.append({"c": "", "s": "pad"})

    flush_full_pages()
    if buf:
        while len(buf) < CAP:
            buf.append({"c": "", "s": "pad"})
        pages.append({"type": "body", "cells": buf})
    return pages


def compact_pages(pages: list[dict]) -> list[dict]:
    compact: list[dict] = []
    for index, page in enumerate(pages):
        page_num = index + 1
        if page["type"] == "opener":
            compact.append(
                {
                    "n": page_num,
                    "t": "o",
                    "lv": page.get("level", "chapter"),
                    "tx": page["text"],
                }
            )
        elif page["type"] == "blank":
            compact.append({"n": page_num, "t": "b"})
        else:
            cols = []
            for col in range(COLS):
                chunk = page["cells"][col * ROWS : (col + 1) * ROWS]
                while chunk and chunk[-1]["s"] in ("pad", "spacer") and not chunk[-1]["c"]:
                    chunk = chunk[:-1]
                if not chunk or all(not cell["c"] for cell in chunk):
                    continue
                chars = "".join(cell["c"] if cell["c"] else "\u200b" for cell in chunk)
                style = "".join(STYLE.get(cell["s"], "0") for cell in chunk)
                if len(set(style)) == 1:
                    style = style[0]
                cols.append({"i": col, "c": chars, "s": style})
            compact.append({"n": page_num, "t": "p", "cols": cols})
    return compact


def png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_carrier(plan_bytes: bytes, path: Path) -> None:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = png_chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
    parts = []
    step = 28000
    for i in range(0, len(plan_bytes), step):
        parts.append(png_chunk(b"bkDt", plan_bytes[i : i + step]))
    header = png_chunk(
        b"bkHd",
        json.dumps(
            {
                "parts": len(parts),
                "bytes": len(plan_bytes),
                "encoding": "utf8-json",
            }
        ).encode(),
    )
    iend = png_chunk(b"IEND", b"")
    path.write_bytes(signature + ihdr + header + b"".join(parts) + idat + iend)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--book",
        type=Path,
        default=Path("data/book-data.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/pages-plan.json"),
    )
    parser.add_argument(
        "--carrier",
        type=Path,
        default=Path("book-data-carrier.png"),
    )
    args = parser.parse_args()

    book = json.loads(args.book.read_text(encoding="utf-8"))
    items = build_items(book)
    pages = paginate(items)
    compact = compact_pages(pages)
    plan = {
        "meta": {
            "rows": ROWS,
            "cols": COLS,
            "fs": 10.5,
            "lh": 14.7,
            "cp": 21.55,
            "cw": 13.125,
            "pages": len(compact),
            "binding": "rtl-odd-right",
        },
        "pages": compact,
    }
    raw = json.dumps(plan, ensure_ascii=False, separators=(",", ":"))
    args.out.write_text(raw, encoding="utf-8")
    write_carrier(raw.encode("utf-8"), args.carrier)
    print(f"pages={len(compact)} json={args.out} carrier={args.carrier}")


if __name__ == "__main__":
    main()
