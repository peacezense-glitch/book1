#!/usr/bin/env python3
"""Build the local Figma plugin from the two source DOCX files."""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "figma-plugin"
MAIN_DOC = ROOT / "《歸源手鏡》.docx"
BACK_DOC = ROOT / "《歸源手鏡》尾頁.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


def paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{W}t":
            parts.append(node.text or "")
        elif node.tag == f"{W}tab":
            parts.append("　")
        elif node.tag in {f"{W}br", f"{W}cr"}:
            parts.append("\n")
    return re.sub(r"[ \t]+", " ", "".join(parts)).strip()


def read_paragraphs(path: Path) -> list[str]:
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find(f".//{W}body")
    if body is None:
        raise ValueError(f"{path.name} has no Word document body")
    return [
        text
        for paragraph in body.iter(f"{W}p")
        if (text := paragraph_text(paragraph))
    ]


def classify(text: str, in_toc: bool) -> str:
    if in_toc:
        return "toc"
    if re.match(r"^第[一二三四五六七八九十百零〇0-9]+卷(?:\s|$)", text):
        return "volume"
    if re.match(r"^第[一二三四五六七八九十百零〇0-9]+章(?:\s|$)", text):
        return "chapter"
    if text in {"自序", "序言", "結語", "後記"}:
        return "major"
    if len(text) <= 30 and (
        re.match(r"^[一二三四五六七八九十]+[、．.]", text)
        or re.match(r"^[0-9]+[、．.]", text)
        or text.endswith("結語")
    ):
        return "heading"
    return "body"


def read_media(path: Path) -> list[dict[str, str]]:
    media: list[dict[str, str]] = []
    with ZipFile(path) as archive:
        names = sorted(
            name for name in archive.namelist() if name.startswith("word/media/")
        )
        for name in names:
            suffix = Path(name).suffix.lower()
            mime = mimetypes.types_map.get(suffix, "application/octet-stream")
            media.append(
                {
                    "name": Path(name).name,
                    "mime": mime,
                    "base64": base64.b64encode(archive.read(name)).decode("ascii"),
                }
            )
    return media


def make_data() -> dict:
    paragraphs = read_paragraphs(MAIN_DOC)
    self_preface_indexes = [i for i, text in enumerate(paragraphs) if text == "自序"]
    body_start = self_preface_indexes[1] if len(self_preface_indexes) > 1 else 0
    manuscript = [
        {
            "text": text,
            "kind": classify(text, index < body_start),
        }
        for index, text in enumerate(paragraphs)
    ]
    return {
        "title": "歸源手鏡",
        "series": "華玉講堂道家叢書60",
        "author": "宏泓道者",
        "isbn": "978-9887-2160-4-9",
        "trim": {"widthMm": 152, "heightMm": 230},
        "paragraphs": manuscript,
        "backMatter": read_paragraphs(BACK_DOC),
        "backMatterImages": read_media(BACK_DOC),
        "source": {
            "main": MAIN_DOC.name,
            "back": BACK_DOC.name,
            "bodyStart": body_start,
        },
    }


def main() -> None:
    for path in (MAIN_DOC, BACK_DOC, PLUGIN_DIR / "plugin.template.js"):
        if not path.exists():
            raise FileNotFoundError(path)

    data = make_data()
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    template = (PLUGIN_DIR / "plugin.template.js").read_text(encoding="utf-8")
    marker = "/*__BOOK_DATA__*/"
    if template.count(marker) != 1:
        raise ValueError(f"Expected exactly one {marker} marker")

    (PLUGIN_DIR / "book-data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (PLUGIN_DIR / "code.js").write_text(
        template.replace(marker, encoded), encoding="utf-8"
    )
    print(
        f"Built plugin: {len(data['paragraphs'])} paragraphs, "
        f"{sum(len(p['text']) for p in data['paragraphs']):,} characters, "
        f"{len(data['backMatterImages'])} embedded images"
    )


if __name__ == "__main__":
    main()
