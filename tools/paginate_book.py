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

# Test Book 5: balanced side margins (binding + outer + text = trim width).
ROWS = 36
COLS = 15
CAP = ROWS * COLS
BINDING_MM = 21
# OUTER companion ≈ pageW − textBlock − binding ≈ 20 mm (exact at render).
OUTER_MM = 20
TOP_MM = 22  # align body / 大標頭 with independent title leaf
BOTTOM_MM = 16
EDITION = "test-book-5"

# Line-start kinsoku: do not open a column with these.
# Note: list bullet 「・」(from 「·」) is stripped before layout — do not treat as kinsoku,
# or it will be moved to the previous column and appear as a stray black dot.
KINSKU_LINE_START = set("，。、：；！？）」』》︶﹂﹄…")

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
    if (
        re.match(r"^第.+卷", text)
        or text in ("自序", "序", "附錄")
        or (text.endswith("序") and "手鏡" in text)
    ):
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
                # Fullwidth ： (not ︓) so horizontal CENTER matches body punct.
                vert_text(strip_spaces(parts[0])) + "：",
                vert_text(strip_spaces(parts[1])),
            ]
        return [vert_text(head), vert_text(strip_spaces(rest))]

    # 附錄X：…
    m = re.match(r"^(附錄[一二三四])[：:](.+)$", compact)
    if m:
        return [vert_text(m.group(1)) + "：", vert_text(m.group(2))]

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
        # Biography / list lines start with 「·」; strip so vertical layout has no
        # orphan 「・」 (kinsoku used to shove them onto the previous column end).
        if kind in ("body", "heading"):
            text = re.sub(r"^[·•･・．.]+", "", text)
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

        if re.search(r"謹[識序]", text):
            match = re.match(r"^(.+謹[識序])\s*(.+)$", text)
            if match and match.group(2).strip():
                items.append({"kind": "signature_name", "text": match.group(1).strip()})
                items.append({"kind": "signature_date", "text": match.group(2).strip()})
            else:
                items.append({"kind": "signature_name", "text": text})
            continue

        classified = classify_body_line(text)
        if classified["kind"] == "tip_then_body":
            items.append({"kind": "tip", "text": classified["label"]})
            items.append({"kind": "body", "text": classified["text"]})
        else:
            items.append(classified)

    # Colophon is horizontal (Test Book 4); not paginated as vertical body.
    return items


def volume_running_title(text: str) -> str:
    """Compact 卷題 for outer running heads (drop long subtitle after ：)."""
    text = strip_spaces(text)
    match = re.match(r"^(第.+?卷)([^：:]*?)[：:].+$", text)
    if match:
        return match.group(1) + match.group(2)
    match = re.match(r"^(附錄[一二三四])", text)
    if match:
        return match.group(1)
    return text


def chinese_digits(n: int) -> str:
    """Digit-wise Chinese numerals (五二 for 52). Kept for non-folio uses."""
    table = "〇一二三四五六七八九"
    return "".join(table[int(ch)] for ch in str(n))


def arabic_folio(n: int) -> str:
    """Page folio as Arabic numerals (12 for 12)."""
    return str(int(n))


def roman_numerals(n: int) -> str:
    """Unused legacy: Roman numerals (XII for 12)."""
    if n <= 0:
        return ""
    pairs = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    out = []
    rest = int(n)
    for value, glyph in pairs:
        while rest >= value:
            out.append(glyph)
            rest -= value
    return "".join(out)


def paginate(items: list[dict]) -> list[dict]:
    pages: list[dict] = []
    buf: list[dict] = []
    items = group_toc_items(items)

    def flush_full_pages() -> None:
        nonlocal buf
        while len(buf) >= CAP:
            page_cells = buf[:CAP]
            rest = buf[CAP:]
            # Avoid a new page that opens with only a few leftover glyphs (孤字跨頁).
            if rest:
                first_len = min(ROWS, len(rest))
                first_col = rest[:first_len]
                content_chars = sum(1 for cell in first_col if cell.get("c"))
                styles = {cell.get("s") for cell in first_col if cell.get("c")}
                if (
                    0 < content_chars <= 4
                    and styles <= {"body"}
                    and len(page_cells) >= ROWS
                ):
                    moved = page_cells[-ROWS:]
                    page_cells = page_cells[:-ROWS]
                    while len(page_cells) < CAP:
                        page_cells.append({"c": "", "s": "pad"})
                    rest = moved + rest
            pages.append({"type": "body", "cells": page_cells})
            buf = rest

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

    def place_body_paragraph(text: str) -> None:
        """Flow a body paragraph into columns; avoid orphan last columns (孤字)."""
        nonlocal buf
        chars = vert(list(text))
        if not chars:
            return
        for ch in chars:
            buf.append({"c": ch, "s": "body"})
        rem = len(buf) % ROWS
        # If the last column of this paragraph is only a few glyphs (often just 。),
        # pull from the previous full column so the remainder stays with the sentence.
        orphan_min = 4
        if 0 < rem <= orphan_min and len(chars) > rem:
            steal = orphan_min - rem
            col_start = len(buf) - rem
            insert_at = col_start - steal
            # Only steal within the previous column of this paragraph.
            para_start = len(buf) - len(chars)
            if insert_at >= para_start:
                for _ in range(steal):
                    buf.insert(insert_at, {"c": "", "s": "pad"})
        while len(buf) % ROWS:
            buf.append({"c": "", "s": "pad"})

    for item in items:
        kind = item["kind"]
        if kind == "opener":
            flush_full_pages()
            if buf:
                pad_to_page_end()
                pages.append({"type": "body", "cells": buf})
                buf = []
            opener = {
                "type": "opener",
                "level": item.get("level", "chapter"),
                "text": item["text"],
                "lines": item.get("lines") or split_opener(item["text"]),
            }
            clean = strip_spaces(item["text"])
            # Plate images requested on specific openers.
            if clean == "自序":
                opener["img"] = "jiutian"
            elif item.get("level") == "volume" and clean.startswith("第五卷"):
                opener["img"] = "luzu"
            pages.append(opener)
            continue

        if kind == "toc_block":
            place_toc_block(item)
            continue

        if kind == "toc_title":
            place_styled_column(item["text"], "toc_bold", blank_before=False)

        elif kind in ("tip", "heading"):
            # Full-page plate of the four masters immediately before 卷六結語 title.
            if kind == "heading" and "第六卷結語" in item["text"]:
                flush_full_pages()
                if buf:
                    pad_to_page_end()
                    pages.append({"type": "body", "cells": buf})
                    buf = []
                pages.append({"type": "illust", "img": "four"})
            style = "tip" if kind == "tip" else "heading"
            # 本章實修功課：獨立起頁，避免落在頁中後段。
            if kind == "tip" and cols_used_in_page() > 0:
                pad_to_page_end()
            # Heading/tip + at least the next column of content stay together.
            place_styled_column(item["text"], style, blank_before=True, keep_cols=3)

        elif kind == "toc_entry":
            place_styled_column(item["text"], "toc_reg", indent=2)

        elif kind == "subhead":
            place_styled_column(
                item["text"], "subhead", blank_before=False, indent=1, keep_cols=2
            )

        elif kind == "book_title":
            # Dedicated title card page (unique design) — not body columns.
            flush_full_pages()
            if buf:
                pad_to_page_end()
                pages.append({"type": "body", "cells": buf})
                buf = []
            pages.append(
                {
                    "type": "title_card",
                    "title": item["text"],
                    "subtitle": "",
                }
            )

        elif kind == "book_subtitle":
            # Attach subtitle to the preceding title_card when possible.
            if pages and pages[-1].get("type") == "title_card" and not pages[-1].get(
                "subtitle"
            ):
                pages[-1]["subtitle"] = item["text"]
            else:
                flush_full_pages()
                if buf:
                    pad_to_page_end()
                    pages.append({"type": "body", "cells": buf})
                    buf = []
                pages.append(
                    {
                        "type": "title_card",
                        "title": "",
                        "subtitle": item["text"],
                    }
                )

        elif kind == "signature_name":
            # Keep 謹識 with the preceding 自序 page; bottom-align in the column.
            name_chars = vert(list(item["text"]))
            place_styled_column(
                item["text"],
                "sign",
                blank_before=True,
                indent=max(0, ROWS - len(name_chars)),
                keep_cols=3,
            )

        elif kind == "signature_date":
            date_chars = vert(list(item["text"]))
            place_styled_column(
                item["text"],
                "sign_date",
                indent=max(0, ROWS - len(date_chars)),
            )

        else:
            place_body_paragraph(item["text"])

    flush_full_pages()
    if buf:
        while len(buf) < CAP:
            buf.append({"c": "", "s": "pad"})
        pages.append({"type": "body", "cells": buf})
    return pages


def apply_kinsoku_compact(compact: list[dict]) -> None:
    """Move leading body punctuation onto the previous column (may exceed ROWS)."""

    def is_body_col(col: dict) -> bool:
        s = str(col.get("s", "0"))
        return s == "0" or (len(s) > 1 and set(s) <= {"0"})

    def peel(text: str) -> tuple[str, str]:
        k = 0
        while k < len(text) and text[k] in KINSKU_LINE_START:
            k += 1
        return text[:k], text[k:]

    for pi, page in enumerate(compact):
        if page.get("t") != "p":
            continue
        for _ in range(COLS * 3):
            cols = sorted(page.get("cols") or [], key=lambda c: c["i"])
            by_i = {c["i"]: c for c in cols}
            moved = False
            for ci in sorted(by_i):
                cur = by_i[ci]
                text = cur.get("c") or ""
                if not text or text[0] not in KINSKU_LINE_START or not is_body_col(cur):
                    continue
                prev = next(
                    (
                        by_i[j]
                        for j in range(ci - 1, -1, -1)
                        if j in by_i and is_body_col(by_i[j])
                    ),
                    None,
                )
                if prev is None and pi > 0:
                    prev_page = compact[pi - 1]
                    if prev_page.get("t") == "p":
                        prev_cols = sorted(
                            prev_page.get("cols") or [], key=lambda c: c["i"]
                        )
                        prev = next(
                            (c for c in reversed(prev_cols) if is_body_col(c)), None
                        )
                if prev is None:
                    continue
                punct, rest = peel(text)
                prev["c"] = (prev.get("c") or "") + punct
                cur["c"] = rest
                if not rest:
                    page["cols"] = [c for c in (page.get("cols") or []) if c.get("c")]
                moved = True
                break
            if not moved:
                break

        cols = sorted(page.get("cols") or [], key=lambda c: c["i"])
        if not cols or pi == 0:
            continue
        first = cols[0]
        text = first.get("c") or ""
        if text and text[0] in KINSKU_LINE_START and is_body_col(first):
            prev_page = compact[pi - 1]
            if prev_page.get("t") != "p":
                continue
            prev_cols = sorted(prev_page.get("cols") or [], key=lambda c: c["i"])
            prev = next((c for c in reversed(prev_cols) if is_body_col(c)), None)
            if prev is None:
                continue
            punct, rest = peel(text)
            prev["c"] = (prev.get("c") or "") + punct
            first["c"] = rest
            if not rest:
                page["cols"] = [c for c in (page.get("cols") or []) if c.get("c")]


def compact_pages(pages: list[dict], *, book_title: str = "歸源手鏡") -> list[dict]:
    compact: list[dict] = []
    running = "總目錄"
    for index, page in enumerate(pages):
        page_num = index + 1
        if page["type"] == "opener":
            level = page.get("level", "chapter")
            text = page["text"]
            if level == "volume":
                running = volume_running_title(text)
            elif level == "major":
                clean = strip_spaces(text) or "自序"
                # Guest/author prefaces: running head is short 序 / 自序 only.
                if clean.endswith("序") and "手鏡" in clean:
                    running = "序"
                else:
                    running = clean
            elif strip_spaces(text).startswith("附錄"):
                running = volume_running_title(text)
            lines = page.get("lines") or split_opener(page["text"])
            entry = {
                "n": page_num,
                "t": "o",
                "lv": level,
                "tx": page["text"],
                "ln": lines,  # semantic vertical columns for designed 断行
                "vh": running,
                "fo": arabic_folio(page_num),
            }
            if page.get("img"):
                entry["img"] = page["img"]
            compact.append(entry)
        elif page["type"] == "illust":
            compact.append(
                {
                    "n": page_num,
                    "t": "i",
                    "img": page.get("img") or "",
                    "vh": running,
                    "fo": arabic_folio(page_num),
                }
            )
        elif page["type"] == "blank":
            compact.append(
                {
                    "n": page_num,
                    "t": "b",
                    "vh": running,
                    "fo": arabic_folio(page_num),
                }
            )
        elif page["type"] == "title_card":
            compact.append(
                {
                    "n": page_num,
                    "t": "tc",
                    "title": page.get("title") or "",
                    "sub": page.get("subtitle") or "",
                    # Dedicated leaf — no body running head; folio only for orientation.
                    "vh": "",
                    "fo": arabic_folio(page_num),
                }
            )
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
            compact.append(
                {
                    "n": page_num,
                    "t": "p",
                    "cols": cols,
                    "vh": running,
                    "fo": arabic_folio(page_num),
                }
            )
    return compact


def build_colophon_qr() -> dict:
    """B/W QR payload for the copyright page (講堂課程登記表 → daohk.com)."""
    try:
        import qrcode
    except ImportError:
        return {
            "title": "講堂課程登記表",
            "url": "www.daohk.com",
            "href": "https://www.daohk.com",
            "matrix": [],
        }
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=2,
    )
    qr.add_data("https://www.daohk.com")
    qr.make(fit=True)
    matrix = [[1 if cell else 0 for cell in row] for row in qr.get_matrix()]
    return {
        "title": "講堂課程登記表",
        "url": "www.daohk.com",
        "href": "https://www.daohk.com",
        "matrix": matrix,
    }


def build_colophon_page(book: dict, page_num: int) -> dict:
    """Horizontal copyright page payload (traditional: only this page is 橫排)."""
    # Keep original spacing — English needs spaces (unlike vertical body).
    # Drop placeholder lines that the QR graphic replaces.
    skip = {"華玉講堂Youtube", "華玉講堂 課程", "華玉講堂課程"}
    matter = []
    for line in book.get("backMatter", []):
        text = (line if isinstance(line, str) else str(line)).strip()
        if text and text not in skip:
            matter.append(text)
    return {
        "n": page_num,
        "t": "c",
        "vh": "版權頁",
        "fo": arabic_folio(page_num),
        "title": book.get("title", "歸源手鏡"),
        "series": book.get("series", ""),
        "author": book.get("author", ""),
        "isbn": book.get("isbn", ""),
        "matter": matter,
        "qr": build_colophon_qr(),
    }


def png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def absorb_short_body_pages(compact: list[dict], *, min_cols: int = 3) -> None:
    """Merge nearly-empty body pages so we rarely leave a leaf with only 1–2 columns.

    Prefer prepending a short page onto the next body page (keeps reading order).
    If the next page cannot take it, append onto the previous body page when room.
    """
    i = 0
    while i < len(compact):
        page = compact[i]
        if page.get("t") != "p":
            i += 1
            continue
        cols = page.get("cols") or []
        if not cols or len(cols) > min_cols:
            i += 1
            continue

        def reindex(cols_list: list[dict]) -> list[dict]:
            out = []
            for j, col in enumerate(cols_list):
                nc = dict(col)
                nc["i"] = j
                out.append(nc)
            return out

        merged = False
        # 1) Prepend onto following body page.
        if i + 1 < len(compact) and compact[i + 1].get("t") == "p":
            nxt = compact[i + 1]
            nxt_cols = nxt.get("cols") or []
            if len(cols) + len(nxt_cols) <= COLS:
                nxt["cols"] = reindex(cols + nxt_cols)
                del compact[i]
                merged = True
        # 2) Else append onto previous body page if room.
        if not merged and i > 0 and compact[i - 1].get("t") == "p":
            prev = compact[i - 1]
            prev_cols = prev.get("cols") or []
            if len(prev_cols) + len(cols) <= COLS:
                prev["cols"] = reindex(prev_cols + cols)
                del compact[i]
                merged = True
                i -= 1
        if merged:
            for j in range(max(i - 1, 0), len(compact)):
                compact[j]["n"] = j + 1
                if "fo" in compact[j]:
                    compact[j]["fo"] = arabic_folio(j + 1)
            continue
        i += 1


def place_four_masters_plate(compact: list[dict]) -> None:
    """Prefer the four-masters plate on folio 295 (odd), immediately before 結語.

    Pagination often leaves a short litany page on 295 and the plate on 296;
    swap those two leaves so the plate sits on 295 as requested.
    """
    idx = next(
        (
            i
            for i, page in enumerate(compact)
            if page.get("t") == "i" and page.get("img") == "four"
        ),
        None,
    )
    if idx is None or idx == 0:
        return
    prev = compact[idx - 1]
    cur = compact[idx]
    if prev.get("t") != "p" or prev.get("n") != 295 or cur.get("n") != 296:
        return
    compact[idx - 1], compact[idx] = cur, prev
    for i in range(idx - 1, len(compact)):
        compact[i]["n"] = i + 1
        if "fo" in compact[i]:
            compact[i]["fo"] = arabic_folio(i + 1)


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
    compact = compact_pages(pages, book_title=book.get("title", "歸源手鏡"))
    apply_kinsoku_compact(compact)
    absorb_short_body_pages(compact, min_cols=3)
    place_four_masters_plate(compact)
    # Horizontal colophon on the next page after body (odd/right preferred).
    next_n = (compact[-1]["n"] + 1) if compact else 1
    # Prefer odd colophon, but use a rendered white blank (not a skipped hole).
    if next_n % 2 == 0:
        compact.append(
            {
                "n": next_n,
                "t": "b",
                "vh": "",
                "fo": arabic_folio(next_n),
            }
        )
        next_n += 1
    compact.append(build_colophon_page(book, next_n))
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
            "bindingMm": BINDING_MM,
            "outerMm": OUTER_MM,
            "topMm": TOP_MM,
            "bottomMm": BOTTOM_MM,
            "pages": len(compact),
            "binding": "rtl-odd-right",
            "runningHead": "volume-outer",
            "colophon": "horizontal",
            "edition": EDITION,
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
