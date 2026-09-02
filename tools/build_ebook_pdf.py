#!/usr/bin/env python3
"""Build ebook PDF from pages-plan: real Unicode text + hi-res images.

Unlike Figma exports (Type 3 glyph outlines) or the 5 MB JPEG re-raster pass,
this renders body copy with embedded Noto Serif TC so text is selectable and
scales cleanly on iPad. Illustration / cover pages embed source PNGs at full
resolution (JPEG-compressed in PDF only at quality 88).
"""

from __future__ import annotations

import argparse
import json
import re
from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image

MM = 72.0 / 25.4
PAGE_W = 152.0 * MM
PAGE_H = 230.0 * MM
ROWS = 42
COLS = 15
BODY_FS = 10.0
BODY_LH = 12.6
CW = 12.5
CP = 21.55
INNER = 21.0 * MM
TOP = 22.0 * MM
HEAD_FS = 7.5
HEAD_LH = 9.5
HEAD_W = 9.5
GAP_BODY = 5.0 * MM
GAP_FOLIO = 10.0 * MM
VOL_GAP = 5.0 * MM
OPENER_TOP = 22.0 * MM
BLACK = (0, 0, 0)
BOLD_STYLES = {"1", "2", "5", "7", "9", "b"}
STYLE_FS = {
    "0": 10,
    "1": 10.5,
    "2": 10.5,
    "5": 10.5,
    "6": 10.5,
    "7": 11.5,
    "8": 10,
    "9": 11.5,
    "a": 10.5,
    "b": 10,
}
ASSETS = {
    "cover": Path("assets/cover-guiyuan.png"),
    "jiutian": Path("assets/illust-jiutian.png"),
    "luzu": Path("assets/illust-luzu.png"),
    "four": Path("assets/illust-four-masters.png"),
    "promo": Path("assets/promo-huayu-2027.png"),
    "qr_course": Path("assets/colophon-qr-course.png"),
    "qr_youtube": Path("assets/colophon-youtube-qr.png"),
}
IMAGE_JPEG_Q = 88
COLOPHON_QR_PAD = 18  # symmetric air above QR plates and below captions
FONT_URLS = {
    "NotoSerifTC-Regular.otf": "https://github.com/notofonts/noto-cjk/raw/main/Serif/OTF/TraditionalChinese/NotoSerifCJKtc-Regular.otf",
    "NotoSerifTC-Bold.otf": "https://github.com/notofonts/noto-cjk/raw/main/Serif/OTF/TraditionalChinese/NotoSerifCJKtc-Bold.otf",
}


def ensure_font(path: Path) -> Path:
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    url = FONT_URLS.get(path.name)
    if not url:
        raise FileNotFoundError(path)
    import urllib.request

    print(f"downloading {path.name} …")
    urllib.request.urlretrieve(url, path)
    return path


def page_margins() -> tuple[float, float, float]:
    text_block_w = (COLS - 1) * CP + CW
    outer = PAGE_W - text_block_w - INNER
    return INNER, outer, text_block_w


def split_running_head(title: str) -> tuple[str, str]:
    clean = title or ""
    vol = re.match(r"^(第[一二三四五六七八九十百千零〇\d]+卷)(.+)$", clean)
    if vol and vol.group(2):
        return vol.group(1), vol.group(2)
    app = re.match(r"^(附錄[一二三四])(.+)$", clean)
    if app and app.group(2):
        return app.group(1), app.group(2)
    return clean, ""


class BookPdf:
    def __init__(self, font_reg: Path, font_bold: Path) -> None:
        self.doc = pymupdf.open()
        self.reg = pymupdf.Font(fontfile=str(font_reg))
        self.bold = pymupdf.Font(fontfile=str(font_bold))

    def new_page(self) -> pymupdf.Page:
        page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        page.insert_font(fontname="NotoSerifTC-R", fontbuffer=self.reg.buffer)
        page.insert_font(fontname="NotoSerifTC-B", fontbuffer=self.bold.buffer)
        return page

    def fonts(self) -> tuple[str, str]:
        return "NotoSerifTC-R", "NotoSerifTC-B"

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(path), deflate=True, garbage=4, clean=True)

    def fit_image_rect(self, img_path: Path, box: pymupdf.Rect, *, fit_width: bool = True) -> pymupdf.Rect:
        """Place image in box without distortion (Figma FIT / fit-to-width)."""
        im = Image.open(img_path)
        iw, ih = im.size
        if iw <= 0 or ih <= 0:
            return box
        box_w = box.width
        box_h = box.height
        if fit_width:
            scale = box_w / iw
            disp_w = box_w
            disp_h = ih * scale
            if disp_h > box_h:
                scale = min(box_w / iw, box_h / ih)
                disp_w = iw * scale
                disp_h = ih * scale
        else:
            scale = min(box_w / iw, box_h / ih)
            disp_w = iw * scale
            disp_h = ih * scale
        x0 = box.x0 + (box_w - disp_w) / 2
        y0 = box.y0 + (box_h - disp_h) / 2
        return pymupdf.Rect(x0, y0, x0 + disp_w, y0 + disp_h)

    def insert_image_file(
        self,
        page: pymupdf.Page,
        img_path: Path,
        rect: pymupdf.Rect,
        *,
        keep_alpha: bool = False,
        fit_width: bool = False,
    ) -> None:
        im = Image.open(img_path)
        if im.mode in ("RGBA", "P") and not keep_alpha:
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
            im = bg
        bio = BytesIO()
        im.save(bio, format="JPEG", quality=IMAGE_JPEG_Q, optimize=True)
        place = self.fit_image_rect(img_path, rect, fit_width=fit_width) if fit_width else rect
        page.insert_image(place, stream=bio.getvalue())

    def draw_running_head(self, page: pymupdf.Page, spec: dict) -> None:
        n = spec.get("n", 1)
        is_odd = n % 2 == 1
        inner, outer, text_block_w = page_margins()
        head, sub = split_running_head(str(spec.get("vh") or ""))
        folio = str(spec.get("fo") or "")
        reg_name, _bold_name = self.fonts()
        x = (
            PAGE_W - outer + GAP_BODY
            if is_odd
            else PAGE_W - inner - text_block_w - GAP_BODY - HEAD_W
        )
        head_chars = [c for c in head if c]
        sub_chars = [c for c in sub if c]
        folio_chars = [c for c in folio if c]
        head_h = max(len(head_chars), 1) * HEAD_LH + 2
        sub_h = len(sub_chars) * HEAD_LH + 2 if sub_chars else 0
        title_block_h = head_h + (VOL_GAP + sub_h if sub_chars else 0)
        title_y = PAGE_H / 2 - GAP_FOLIO / 2 - title_block_h
        folio_y = PAGE_H / 2 + GAP_FOLIO / 2

        def vhead(chars: list[str], y0: float) -> None:
            for i, ch in enumerate(chars):
                self._insert_centered(
                    page, x, y0 + i * HEAD_LH, HEAD_W, HEAD_LH, ch, self.reg, HEAD_FS, reg_name
                )

        if head_chars:
            vhead(head_chars, title_y)
        if sub_chars:
            vhead(sub_chars, title_y + head_h + VOL_GAP)
        if folio_chars:
            vhead(folio_chars, folio_y)

    def _insert_centered(
        self,
        page: pymupdf.Page,
        x: float,
        y: float,
        w: float,
        h: float,
        ch: str,
        font: pymupdf.Font | str,
        fs: float,
        fontname: str,
    ) -> None:
        if not ch or ch == "\u200b":
            return
        if isinstance(font, pymupdf.Font):
            tw = font.text_length(ch, fontsize=fs)
        else:
            tw = fs
        tx = x + (w - tw) / 2
        ty = y + h * 0.72
        page.insert_text((tx, ty), ch, fontname=fontname, fontsize=fs, color=BLACK)

    def draw_body_cols(self, page: pymupdf.Page, cols: list[dict], is_odd: bool) -> None:
        inner, outer, _ = page_margins()
        right_margin = outer if is_odd else inner
        right_edge = PAGE_W - right_margin - CW
        reg_name, bold_name = self.fonts()
        for col in cols:
            text = col.get("c") or ""
            if not text:
                continue
            styles = col.get("s") or "0"
            if len(styles) == 1:
                styles = styles * len(text)
            indent = col.get("d") or 0
            fs_default = col.get("fs") or BODY_FS
            i = 0
            while i < len(text):
                s0 = styles[i] if i < len(styles) else "0"
                j = i + 1
                while j < len(text) and (styles[j] if j < len(styles) else "0") == s0:
                    j += 1
                fs = STYLE_FS.get(s0, fs_default)
                fname = bold_name if s0 in BOLD_STYLES else reg_name
                fobj = self.bold if s0 in BOLD_STYLES else self.reg
                x = right_edge - col["i"] * CP
                for k, ch in enumerate(text[i:j]):
                    if ch == "\u200b":
                        continue
                    y = TOP + (indent + i + k) * BODY_LH
                    self._insert_centered(page, x - CW, y, CW, BODY_LH, ch, fobj, fs, fname)
                i = j

    def draw_opener(self, page: pymupdf.Page, spec: dict, is_odd: bool) -> None:
        img_key = spec.get("img")
        if img_key and img_key in ASSETS:
            inner, outer, text_block_w = page_margins()
            top = TOP
            bottom_pad = 18 * MM
            box_x = inner if is_odd else outer
            box_h = max(80, PAGE_H - top - bottom_pad)
            rect = pymupdf.Rect(box_x, top, box_x + text_block_w, top + box_h)
            self.insert_image_file(page, ASSETS[img_key], rect, fit_width=True)
            return
        lines = spec.get("ln") or [spec.get("tx") or ""]
        fs = 15 if spec.get("lv") == "major" else 17
        lh = 20 if spec.get("lv") == "major" else 23
        col_w = 28
        pitch = 37
        n = max(len(lines), 1)
        group_w = col_w + (n - 1) * pitch
        rightmost_x = PAGE_W / 2 + group_w / 2 - col_w
        _, bold_name = self.fonts()
        tallest = 0.0
        for i, line in enumerate(lines):
            chars = list(str(line))
            if not chars:
                continue
            colon = None
            if chars[-1] in ("：", ":", "︓"):
                colon = "："
                chars = chars[:-1]
            h = len(chars) * lh + 2
            tallest = max(tallest, h + (lh if colon else 0))
            col_x = rightmost_x - i * pitch
            for j, ch in enumerate(chars):
                self._insert_centered(page, col_x, OPENER_TOP + j * lh, col_w, lh, ch, self.bold, fs, bold_name)
            if colon:
                self._insert_centered(
                    page,
                    col_x,
                    OPENER_TOP + len(chars) * lh,
                    col_w,
                    lh,
                    colon,
                    self.bold,
                    fs,
                    bold_name,
                )
        rule = pymupdf.Rect(rightmost_x + col_w + 14, OPENER_TOP, rightmost_x + col_w + 14.7, OPENER_TOP + max(tallest, 220))
        page.draw_rect(rule, color=BLACK, fill=BLACK)

    def draw_illust(self, page: pymupdf.Page, spec: dict, is_odd: bool) -> None:
        img_key = spec.get("img") or ""
        if spec.get("bleed") or img_key in ("promo", "endcircle"):
            path = ASSETS.get(img_key, ASSETS["promo"])
            self.insert_image_file(page, path, pymupdf.Rect(0, 0, PAGE_W, PAGE_H))
            return
        inner, outer, text_block_w = page_margins()
        top = TOP
        bottom_pad = 16 * MM
        box_x = inner if is_odd else outer
        box_h = max(80, PAGE_H - top - bottom_pad)
        rect = pymupdf.Rect(box_x, top, box_x + text_block_w, top + box_h)
        self.insert_image_file(page, ASSETS[img_key], rect, fit_width=True)

    def draw_title_card(self, page: pymupdf.Page, spec: dict) -> None:
        title = spec.get("title") or ""
        subtitle = spec.get("sub") or ""
        title_fs = 17
        title_lh = 24
        sub_fs = 10.5
        sub_lh = 15
        col_w = 28
        pitch = 40
        sub_gap = 18
        colon_idx = max(title.find("："), title.find(":"))
        if colon_idx > 0:
            title_cols = [title[:colon_idx], title[colon_idx + 1 :]]
            title_cols = [c for c in title_cols if c]
        else:
            title_cols = [title] if title else []
        group_w = col_w + max(len(title_cols) - 1, 0) * pitch + (pitch + sub_gap if subtitle else 0)
        rightmost_x = PAGE_W / 2 + group_w / 2 - col_w
        _, bold_name = self.fonts()
        reg_name, _bold_name = self.fonts()
        title_heights = []
        for i, col in enumerate(title_cols):
            chars = list(col)
            extra = title_lh if colon_idx > 0 and i == 0 else 0
            title_heights.append(len(chars) * title_lh + extra + 4)
        sub_h = len(subtitle) * sub_lh + 4 if subtitle else 0
        block_h = max(*(title_heights or [0]), sub_h, 220)
        top = (PAGE_H - block_h) / 2 - 8
        rule = pymupdf.Rect(rightmost_x + col_w + 18, top, rightmost_x + col_w + 18.7, top + block_h)
        page.draw_rect(rule, color=BLACK, fill=BLACK)
        for i, col in enumerate(title_cols):
            chars = list(col)
            col_x = rightmost_x - i * pitch
            for j, ch in enumerate(chars):
                self._insert_centered(page, col_x, top + j * title_lh, col_w, title_lh, ch, self.bold, title_fs, bold_name)
            if i == 0 and colon_idx > 0:
                self._insert_centered(
                    page,
                    col_x,
                    top + len(chars) * title_lh,
                    col_w,
                    title_lh,
                    "：",
                    self.bold,
                    title_fs,
                    bold_name,
                )
        if subtitle:
            chars = list(subtitle)
            col_x = rightmost_x - len(title_cols) * pitch - sub_gap
            for j, ch in enumerate(chars):
                self._insert_centered(page, col_x, top + 48 + j * sub_lh, col_w, sub_lh, ch, self.reg, sub_fs, reg_name)

    def _place_colophon_qr_pair(
        self,
        page: pymupdf.Page,
        margin_x: float,
        y: float,
        content_w: float,
        qr: dict | None = None,
    ) -> float:
        qr = qr or {}
        course = qr.get("course") or {}
        youtube = qr.get("youtube") or {}
        reg_name, _ = self.fonts()
        qr_size = 72
        pad = 7
        cell = qr_size + pad * 2
        gap = 28
        pair_w = cell * 2 + gap
        start_x = margin_x + (content_w - pair_w) / 2
        for dx, asset in ((0, "qr_course"), (cell + gap, "qr_youtube")):
            plate = pymupdf.Rect(start_x + dx, y, start_x + dx + cell, y + cell)
            page.draw_rect(plate, color=(0.55, 0.55, 0.55), fill=(1, 1, 1), width=0.5)
            img_rect = pymupdf.Rect(plate.x0 + pad, plate.y0 + pad, plate.x1 - pad, plate.y1 - pad)
            self.insert_image_file(page, ASSETS[asset], img_rect, keep_alpha=True)
        y += cell + 8
        cap_w = cell + 12
        for dx, label in (
            (0, course.get("caption") or "講堂課程登記表"),
            (cell + gap, youtube.get("caption") or "Youtube"),
        ):
            cap_x = start_x + dx - 6
            tw = len(label) * 7.5
            page.insert_text(
                (cap_x + (cap_w - tw) / 2, y + 9),
                label,
                fontname=reg_name,
                fontsize=7.5,
                color=BLACK,
            )
        return y + 12

    def draw_colophon(self, page: pymupdf.Page, spec: dict) -> None:
        margin_x = 26
        content_w = PAGE_W - margin_x * 2
        label_w = 105
        indent_x = margin_x + label_w
        _, bold_name = self.fonts()
        reg_name, _bold_name = self.fonts()
        y = 28.0
        title = spec.get("title") or "歸源手鏡"
        page.insert_text((margin_x, y + 14), f"《{title}》", fontname=bold_name, fontsize=14, color=BLACK)
        y += 26
        matter = list(spec.get("matter") or [])
        i = 1 if matter and "歸源手鏡" in matter[0] else 0
        while i < len(matter) and "／" in matter[i] and not re.match(
            r"^(版次|國際書號|圖書類別|特別鳴謝)／", matter[i]
        ):
            line = matter[i]
            idx = line.index("／")
            page.insert_text((margin_x, y + 10), line[: idx + 1], fontname=reg_name, fontsize=8.5, color=BLACK)
            page.insert_text((margin_x + label_w, y + 10), line[idx + 1 :].lstrip(), fontname=reg_name, fontsize=8.5, color=BLACK)
            y += 12
            i += 1
        y += 4
        while i < len(matter) and "／" not in matter[i] and not re.search(
            r"掃瞄二維碼|掃描二維碼|All Rights? Reserved|版權所有|免責聲明|Nothing may be reprinted|Youtube|華玉講堂\s*課程",
            matter[i],
        ):
            page.insert_text((indent_x, y + 9), matter[i], fontname=reg_name, fontsize=7.5, color=BLACK)
            y += 11
            i += 1
        y += 8
        while i < len(matter) and "／" in matter[i]:
            line = matter[i]
            idx = line.index("／")
            page.insert_text((margin_x, y + 10), line[: idx + 1], fontname=reg_name, fontsize=8, color=BLACK)
            page.insert_text((margin_x + label_w, y + 10), line[idx + 1 :].lstrip(), fontname=reg_name, fontsize=8, color=BLACK)
            y += 12
            i += 1
        rest = matter[i:]
        legal_start = next(
            (
                j
                for j, line in enumerate(rest)
                if re.search(r"All Rights? Reserved|版權所有|免責聲明|Nothing may be reprinted", line)
            ),
            -1,
        )
        before_legal = rest if legal_start == -1 else rest[:legal_start]
        legal = [] if legal_start == -1 else rest[legal_start:]
        qr_placed = False
        for line in before_legal:
            if re.search(r"Youtube|華玉講堂\s*課程$", line):
                continue
            if re.search(r"掃瞄二維碼|掃描二維碼|掃描二維|掃瞄二維", line):
                y += 20
                page.insert_text((margin_x, y + 10), line, fontname=reg_name, fontsize=8, color=BLACK)
                y += 12 + COLOPHON_QR_PAD
                y = self._place_colophon_qr_pair(page, margin_x, y, content_w, spec.get("qr"))
                qr_placed = True
                continue
            page.insert_text((margin_x, y + 10), line, fontname=reg_name, fontsize=8, color=BLACK)
            y += 12
        if not qr_placed:
            y += 10 + COLOPHON_QR_PAD
            y = self._place_colophon_qr_pair(page, margin_x, y, content_w, spec.get("qr"))
        y = min(y + COLOPHON_QR_PAD, PAGE_H - 18 * MM - len(legal) * 16)
        for line in legal:
            h = 48 if len(line) > 90 else 36 if len(line) > 60 else 14
            page.insert_text((margin_x, y + h - 2), line, fontname=reg_name, fontsize=6.5, color=BLACK)
            y += h + 2


def build(plan_path: Path, out_path: Path, font_reg: Path, font_bold: Path) -> None:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    book = BookPdf(font_reg, font_bold)

    # Cover (outside interior folio sequence).
    cover_page = book.new_page()
    book.insert_image_file(cover_page, ASSETS["cover"], pymupdf.Rect(0, 0, PAGE_W, PAGE_H))

    for spec in plan["pages"]:
        page = book.new_page()
        n = spec["n"]
        is_odd = n % 2 == 1
        t = spec.get("t")
        if t == "b":
            book.draw_running_head(page, spec)
            continue
        if t == "o":
            book.draw_opener(page, spec, is_odd)
        elif t == "p":
            book.draw_body_cols(page, spec.get("cols") or [], is_odd)
        elif t == "i":
            book.draw_illust(page, spec, is_odd)
        elif t == "tc":
            book.draw_title_card(page, spec)
        elif t == "c":
            book.draw_colophon(page, spec)
        skip_head = t == "c" or (t == "i" and (spec.get("img") in ("promo", "endcircle") or spec.get("bleed")))
        if not skip_head:
            book.draw_running_head(page, spec)

    book.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("data/pages-plan.json"))
    parser.add_argument("--out", type=Path, default=Path("exports/歸源手鏡-ebook.pdf"))
    parser.add_argument(
        "--font-reg",
        type=Path,
        default=Path("assets/fonts/NotoSerifTC-Regular.otf"),
    )
    parser.add_argument(
        "--font-bold",
        type=Path,
        default=Path("assets/fonts/NotoSerifTC-Bold.otf"),
    )
    args = parser.parse_args()
    ensure_font(args.font_reg)
    ensure_font(args.font_bold)
    build(args.plan, args.out, args.font_reg, args.font_bold)
    size = args.out.stat().st_size
    print(f"built {args.out} ({size/1024/1024:.2f} MB, {size} bytes)")


if __name__ == "__main__":
    main()
