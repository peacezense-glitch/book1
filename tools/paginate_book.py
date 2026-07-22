#!/usr/bin/env python3
"""Paginate《歸源手鏡》into vertical RTL page plan for Figma.

Binding: odd pages on the RIGHT, even pages on the LEFT (直排右翻).
Body metrics default to 10.5 pt / 14.7 lh / 15×32 grid.

Typography is semantic: manuscript labels (e.g.「副標題：」) are never
printed; role (書名／副題／小標題／提示／落款…) drives weight, size, indent.
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

# Editorial / manuscript labels — never appear in the printed book.
LABEL_RE = re.compile(
    r"^(副標題|標題|小標題|章名|節名|卷名|書名|作者|題記)[：:]"
)

TIP_LABEL_RE = re.compile(
    r"^(本章實修功課|實戰練習|實戰誤區辨析|主功課|輔助功課|今天的功課)([：:].*)?$"
)

# Mid-level structural lines that should read as designed subheads, not body.
SUBHEAD_RE = re.compile(
    r"^("
    r"第[一二三四五六七八九十]+(把刀|步|階段|層|綱|類)"
    r"|誤區[一二三四]"
    r"|.+的起點"
    r"|總結本章"
    r"|四弘誓願|自性三皈依"
    r"|晨間|日間|晚間"
    r"|主修.+路線|各路線通用週課"
    r"|初參第.+年|第[二三五七]年"
    r")([：:].*)?$"
)

# Person-name labels in appendix (short, no period).
NAME_LABEL_RE = re.compile(
    r"^(六祖惠能|憨山德清|憨山大師|虛雲演徹|虛雲老和尚|呂洞賓祖師|呂洞賓)"
    r"(（.+）)?$"
)

APPENDIX_RE = re.compile(r"^附錄[一二三四][：:]")
PREFACE_SECTION_RE = re.compile(r"^(序言|前言)[：:]")
SECTION_HEAD_RE = re.compile(r"^[一二三四五六七八九十]+、")
ARABIC_LIST_HEAD_RE = re.compile(r"^\d+\.\s*")
BOOK_TITLE_RE = re.compile(r"^︽.+︾$")

VERTICAL_FORMS = {
    # Comma/period/colon stay fullwidth (Test Book 2): they center in the cell.
    # Brackets use vertical presentation forms.
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
    "－": "︱",
    "–": "︱",
    "…": "︙",
    "·": "・",
}

# Style codes embedded in pages-plan / carrier for Figma render.
STYLE = {
    "body": "0",
    "heading": "1",  # 小標題 一、… — Bold 11
    "tip": "2",  # 提示／功課標 — Bold 11
    "spacer": "3",
    "pad": "4",
    "toc_bold": "5",  # TOC volume/title — Bold 11
    "toc_reg": "6",  # TOC chapter — Regular 11 + indent
    "sign": "7",  # 落款署名 — Bold 12
    "sign_date": "8",  # 落款年月 — Regular 10.5
    "book_title": "9",  # 書名 — Bold 12
    "book_sub": "a",  # 副題（無「副標題」二字）— Regular 11
    "subhead": "b",  # 次級標 — Bold 10.5 + indent
}

FONT_SIZE = {
    "0": 10.5,
    "1": 11,
    "2": 11,
    "5": 11,
    "6": 11,
    "7": 12,
    "8": 10.5,
    "9": 12,
    "a": 11,
    "b": 10.5,
}


def strip_spaces(text: str) -> str:
    return re.sub(r"[\u3000\s]+", "", text)


def vert(chars: list[str]) -> list[str]:
    return [VERTICAL_FORMS.get(ch, ch) for ch in chars]


def strip_label(text: str) -> tuple[str | None, str]:
    """If text starts with an editorial label, return (label, content)."""
    match = LABEL_RE.match(text)
    if not match:
        return None, text
    return match.group(1), text[match.end() :]


def is_true_heading(text: str) -> bool:
    """Keep classical 一、二、… and volume 結語; demote Arabic list heads."""
    if ARABIC_LIST_HEAD_RE.match(text):
        return False
    if SECTION_HEAD_RE.match(text):
        return True
    if text.endswith("結語") or "結語與" in text:
        return True
    return False


def classify_toc(text: str) -> str:
    """Match original Test Book TOC hierarchy: bold volumes, indented chapters."""
    if "總目錄" in text or text == "目錄":
        return "toc_title"
    if re.match(r"^第.+卷", text) or text in ("自序", "附錄"):
        return "toc_volume"
    return "toc_entry"


def vert_text(text: str) -> str:
    """Apply vertical punctuation forms to a whole string."""
    return "".join(vert(list(text)))


def split_opener(text: str) -> list[str]:
    """Break chapter/volume/appendix titles into designed vertical columns.

    Chapter — 第一章 心的地圖——四家共指之處 →
      第一章 ｜ 心的地圖｜｜ ｜ 四家共指之處
    (dash attaches to the main title column, not its own column)
    """
    raw = text.strip()
    compact = strip_spaces(raw)

    # 第X章 …——…
    m = re.match(
        r"^(第[一二三四五六七八九十百零〇两兩\d]+章)\s*(.+)$",
        raw,
    )
    if m:
        head, rest = m.group(1), m.group(2)
        parts = re.split(r"[—─－-]{2,}|——|──", rest, maxsplit=1)
        if len(parts) == 2 and strip_spaces(parts[0]) and strip_spaces(parts[1]):
            return [
                vert_text(head),
                vert_text(strip_spaces(parts[0])) + "｜｜",
                vert_text(strip_spaces(parts[1])),
            ]
        return [vert_text(head), vert_text(strip_spaces(rest))]

    # 第X卷 …：…
    m = re.match(
        r"^(第[一二三四五六七八九十百零〇两兩\d]+卷)\s*(.+)$",
        raw,
    )
    if m:
        head, rest = m.group(1), m.group(2)
        parts = re.split(r"[：:]", rest, maxsplit=1)
        if len(parts) == 2 and strip_spaces(parts[0]) and strip_spaces(parts[1]):
            return [
                vert_text(head),
                vert_text(strip_spaces(parts[0])) + "︓",
                vert_text(strip_spaces(parts[1])),
            ]
        return [vert_text(head), vert_text(strip_spaces(rest))]

    # 附錄X：…
    m = re.match(r"^(附錄[一二三四])[：:](.+)$", compact)
    if m:
        return [vert_text(m.group(1)) + "︓", vert_text(m.group(2))]

    return [vert_text(compact)]


def group_toc_items(items: list[dict]) -> list[dict]:
    """Wrap TOC volume + its entries so they can keep together across pages."""
    out: list[dict] = []
    i = 0
    while i < len(items):
        item = items[i]
        if item["kind"] == "toc_volume":
            group = [item]
            j = i + 1
            while j < len(items) and items[j]["kind"] == "toc_entry":
                group.append(items[j])
                j += 1
            out.append({"kind": "toc_block", "items": group})
            i = j
            continue
        out.append(item)
        i += 1
    return out


def classify_body_line(text: str) -> dict:
    """Semantic role for a body-kind paragraph, by meaning not raw dump."""
    label, content = strip_label(text)
    if label == "副標題" and content:
        return {"kind": "book_subtitle", "text": content}
    if label and content:
        # Other editorial labels → treat remaining text as designed subtitle/tip.
        return {"kind": "tip", "text": content}

    if APPENDIX_RE.match(text):
        return {
            "kind": "opener",
            "level": "chapter",
            "text": text,
            "lines": split_opener(text),
        }

    if PREFACE_SECTION_RE.match(text):
        return {"kind": "heading", "text": text}

    if BOOK_TITLE_RE.match(text) and ("實修" in text or "手鏡" in text):
        return {"kind": "book_title", "text": text}

    tip = TIP_LABEL_RE.match(text)
    if tip:
        label = tip.group(1)
        rest = (tip.group(2) or "").lstrip("：:")
        # Short tip line → whole tip. Long instruction → tip label + body.
        if not rest or len(rest) <= 12:
            return {"kind": "tip", "text": text}
        return {"kind": "tip_then_body", "label": label + "：", "text": rest}

    if NAME_LABEL_RE.match(text):
        return {"kind": "subhead", "text": text}

    if SUBHEAD_RE.match(text) and len(text) <= 28:
        return {"kind": "subhead", "text": text}

    # Soft mid-heads like「本週，…」opening a tip block.
    if text.startswith("本週") and len(text) <= 40:
        return {"kind": "tip", "text": text}

    return {"kind": "body", "text": text}


def build_items(book: dict) -> list[dict]:
    paragraphs = book["paragraphs"]
    items: list[dict] = []

    for paragraph in paragraphs:
        if paragraph["kind"] != "toc":
            break
        text = strip_spaces(paragraph["text"])
        text = re.sub(r"^[·•･・．.]+", "", text)
        if not text:
            continue
        if "全書內容總結" in text:
            break
        items.append({"kind": classify_toc(text), "text": text})

    start = next(i for i, p in enumerate(paragraphs) if p["kind"] != "toc")
    end = 2098  # before duplicate colophon dump in paragraphs
    for paragraph in paragraphs[start:end]:
        kind = paragraph["kind"]
        text = strip_spaces(paragraph["text"])
        if not text:
            continue

        if kind in ("volume", "chapter", "major"):
            # Use original spacing to detect title breaks (章␠題——副題).
            original = paragraph["text"].strip()
            items.append(
                {
                    "kind": "opener",
                    "level": kind,
                    "text": strip_spaces(original),
                    "lines": split_opener(original),
                }
            )
            continue

        if kind == "heading":
            if is_true_heading(text):
                items.append({"kind": "heading", "text": text})
            elif TIP_LABEL_RE.match(text):
                items.append(classify_body_line(text))
            else:
                # Mis-tagged list / mid lines → subhead, not body soup.
                items.append({"kind": "subhead", "text": text})
            continue

        if "謹識" in text:
            match = re.match(r"^(.+謹識)(.+)$", text)
            if match:
                items.append({"kind": "signature_name", "text": match.group(1)})
                items.append({"kind": "signature_date", "text": match.group(2)})
            else:
                items.append({"kind": "signature_name", "text": text})
            continue

        classified = classify_body_line(text)
        if classified["kind"] == "tip_then_body":
            items.append({"kind": "tip", "text": classified["label"]})
            items.append({"kind": "body", "text": classified["text"]})
        else:
            items.append(classified)

    items.append(
        {
            "kind": "opener",
            "level": "chapter",
            "text": "版權頁",
            "lines": ["版權頁"],
        }
    )
    for line in book.get("backMatter", []):
        text = strip_spaces(line if isinstance(line, str) else str(line))
        if text:
            items.append({"kind": "body", "text": text})
    return items


def paginate(items: list[dict]) -> list[dict]:
    pages: list[dict] = []
    buf: list[dict] = []
    items = group_toc_items(items)

    def flush_full_pages() -> None:
        nonlocal buf
        while len(buf) >= CAP:
            pages.append({"type": "body", "cells": buf[:CAP]})
            buf = buf[CAP:]

    def ensure_column_break() -> None:
        nonlocal buf
        if buf and len(buf) % ROWS:
            while len(buf) % ROWS:
                buf.append({"c": "", "s": "pad"})

    def add_blank_column() -> None:
        nonlocal buf
        ensure_column_break()
        for _ in range(ROWS):
            buf.append({"c": "", "s": "spacer"})

    def cols_used_in_page() -> int:
        ensure_column_break()
        return (len(buf) % CAP) // ROWS

    def remaining_cols() -> int:
        return COLS - cols_used_in_page()

    def pad_to_page_end() -> None:
        nonlocal buf
        ensure_column_break()
        while len(buf) % CAP:
            buf.append({"c": "", "s": "pad"})

    def place_styled_column(
        text: str,
        style: str,
        *,
        blank_before: bool = False,
        indent: int = 0,
        keep_cols: int = 1,
    ) -> None:
        """Place one styled column; keep_cols = total columns that must stay together."""
        nonlocal buf
        chars = vert(list(text))
        need_cols = (1 if blank_before else 0) + 1
        # If this column starts a larger keep-together group, reserve keep_cols.
        reserve = max(need_cols, keep_cols)
        if remaining_cols() < reserve:
            pad_to_page_end()
        if blank_before and (len(buf) % CAP):
            add_blank_column()
        ensure_column_break()
        for _ in range(indent):
            buf.append({"c": "", "s": "pad"})
        for ch in chars:
            buf.append({"c": ch, "s": style})
        while len(buf) % ROWS:
            buf.append({"c": "", "s": "pad"})

    def place_toc_block(block: dict) -> None:
        """Keep a volume (or 附錄) + all its entries on one page when possible."""
        group = block["items"]
        # blank before volume if page already has content
        need = (1 if (len(buf) % CAP) else 0) + len(group)
        if need <= COLS and remaining_cols() < need:
            pad_to_page_end()
        # If group itself is larger than a page, fall through and let it flow.
        for idx, entry in enumerate(group):
            if entry["kind"] == "toc_volume":
                place_styled_column(
                    entry["text"],
                    "toc_bold",
                    blank_before=True,
                    indent=0,
                    keep_cols=1,
                )
            else:
                place_styled_column(entry["text"], "toc_reg", indent=2, keep_cols=1)

    for item in items:
        kind = item["kind"]
        if kind == "opener":
            flush_full_pages()
            if buf:
                pad_to_page_end()
                pages.append({"type": "body", "cells": buf})
                buf = []
            pages.append(
                {
                    "type": "opener",
                    "level": item.get("level", "chapter"),
                    "text": item["text"],
                    "lines": item.get("lines") or split_opener(item["text"]),
                }
            )
            continue

        if kind == "toc_block":
            place_toc_block(item)
            continue

        if kind == "toc_title":
            place_styled_column(item["text"], "toc_bold", blank_before=False)

        elif kind in ("tip", "heading"):
            style = "tip" if kind == "tip" else "heading"
            # Heading/tip + at least the next column of content stay together.
            place_styled_column(item["text"], style, blank_before=True, keep_cols=3)

        elif kind == "toc_entry":
            place_styled_column(item["text"], "toc_reg", indent=2)

        elif kind == "subhead":
            place_styled_column(
                item["text"], "subhead", blank_before=False, indent=1, keep_cols=2
            )

        elif kind == "book_title":
            # 書名 + 副題 keep together (2 cols + trailing blank handled on subtitle).
            place_styled_column(
                item["text"], "book_title", blank_before=False, indent=3, keep_cols=3
            )

        elif kind == "book_subtitle":
            place_styled_column(item["text"], "book_sub", blank_before=False, indent=7)
            add_blank_column()

        elif kind == "signature_name":
            # 落款名 + 年月 + 書名 + 副題 ≈ 4 content cols + blanks
            if buf:
                add_blank_column()
            place_styled_column(
                item["text"], "sign", indent=6, keep_cols=6
            )

        elif kind == "signature_date":
            place_styled_column(item["text"], "sign_date", indent=10)
            add_blank_column()

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
            lines = page.get("lines") or split_opener(page["text"])
            compact.append(
                {
                    "n": page_num,
                    "t": "o",
                    "lv": page.get("level", "chapter"),
                    "tx": page["text"],
                    "ln": lines,  # semantic vertical columns for designed 断行
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
                indent = 0
                while chunk and not chunk[0]["c"] and chunk[0]["s"] in ("pad", "spacer"):
                    indent += 1
                    chunk = chunk[1:]
                if not chunk or all(not cell["c"] for cell in chunk):
                    continue
                chars = "".join(cell["c"] if cell["c"] else "\u200b" for cell in chunk)
                style = "".join(STYLE.get(cell["s"], "0") for cell in chunk)
                if len(set(style)) == 1:
                    style = style[0]
                entry = {"i": col, "c": chars, "s": style}
                if indent:
                    entry["d"] = indent
                sample_style = style[0] if style else "0"
                fs = FONT_SIZE.get(sample_style, 10.5)
                if fs != 10.5:
                    entry["fs"] = fs
                cols.append(entry)
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
    parser.add_argument("--book", type=Path, default=Path("data/book-data.json"))
    parser.add_argument("--out", type=Path, default=Path("data/pages-plan.json"))
    parser.add_argument("--carrier", type=Path, default=Path("book-data-carrier.png"))
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
            "tocFs": 11,
            "headFs": 11,
            "tipFs": 11,
            "signFs": 12,
            "titleFs": 12,
            "subFs": 11,
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

    from collections import Counter

    kinds = Counter(i["kind"] for i in items)
    print(f"pages={len(compact)} json={args.out} carrier={args.carrier}")
    print("items", dict(kinds))


if __name__ == "__main__":
    main()
