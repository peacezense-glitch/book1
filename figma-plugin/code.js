const PT_PER_MM = 72 / 25.4;
const ROWS = 32;
const COLS = 15;
const PAGE_CAPACITY = ROWS * COLS;
const BLACK = { r: 0, g: 0, b: 0 };
const WHITE = { r: 1, g: 1, b: 1 };
const GENERATED_SECTION_NAME = "Guiyuan Interior";

const VERTICAL_FORMS = {
  "，": "︐", "、": "︑", "。": "︒", "：": "︓", "；": "︔",
  "！": "︕", "？": "︖", "「": "﹁", "」": "﹂", "『": "﹃",
  "』": "﹄", "（": "︵", "）": "︶", "【": "︻", "】": "︼",
  "《": "︽", "》": "︾", "〈": "︿", "〉": "﹀", "〔": "︹",
  "〕": "︺", "［": "﹇", "］": "﹈", "—": "︱", "─": "︱",
  "…": "︙", "·": "・"
};

// Centered punctuation: geometric vector marks at cell center (no font side-bearings).
// Direct page children — no 標點層. Body cells hold ideographic space.
const CENTER_PUNCT = new Set(["，", "。", "、", "：", "；", "！", "？", "︐", "︒", "︑", "︓", "︔", "︕", "︖"]);
const PUNCT_NAME = {
  "，": "︐", "。": "︒", "、": "︑", "：": "︓", "；": "︔", "！": "︕", "？": "︖",
  "︐": "︐", "︒": "︒", "︑": "︑", "︓": "︓", "︔": "︔", "︕": "︕", "︖": "︖"
};

figma.showUI(__html__, { width: 400, height: 620, themeColors: true });

function verticalize(text) {
  return Array.from(String(text).replace(/\s+/g, " ")).map(
    (character) => VERTICAL_FORMS[character] || character
  );
}

function chooseFonts(available) {
  const fonts = available.map((entry) => entry.fontName);
  const preferences = [
    ["Noto Serif TC", "Regular", "Bold"],
    ["Source Han Serif TC", "Regular", "Bold"],
    ["Noto Serif CJK TC", "Regular", "Bold"],
    ["Songti TC", "Regular", "Bold"],
    ["PMingLiU", "Regular", "Bold"],
    ["Inter", "Regular", "Bold"]
  ];
  for (const [family, regularStyle, boldStyle] of preferences) {
    const regular = fonts.find(
      (font) => font.family === family && font.style === regularStyle
    );
    if (!regular) continue;
    const bold =
      fonts.find((font) => font.family === family && font.style === boldStyle) ||
      regular;
    return { regular, bold };
  }
  if (!fonts.length) throw new Error("No available fonts in Figma.");
  return { regular: fonts[0], bold: fonts[0] };
}

function pageSize(book) {
  return {
    width: book.trim.widthMm * PT_PER_MM,
    height: book.trim.heightMm * PT_PER_MM
  };
}

function splitRange(book, paragraphs, options) {
  const pages = [];
  if (options.includeFront) {
    pages.push(
      { type: "half-title", heading: book.title },
      { type: "blank" },
      { type: "title", heading: book.title },
      { type: "blank" }
    );
  }

  let buffer = [];
  let runningHeading = options.runningHeading || "正文";
  const flush = () => {
    while (buffer.length) {
      pages.push({
        type: "body",
        heading: runningHeading,
        content: buffer.splice(0, PAGE_CAPACITY)
      });
    }
  };

  for (const paragraph of paragraphs) {
    const isOpener = ["volume", "chapter", "major"].includes(paragraph.kind);
    if (isOpener) {
      flush();
      if ((pages.length + 1) % 2 === 0) pages.push({ type: "blank" });
      runningHeading = paragraph.text;
      pages.push({
        type: "opener",
        heading: paragraph.text,
        level: paragraph.kind
      });
      continue;
    }
    const prefix = paragraph.kind === "heading" ? "　" : "　　";
    const characters = verticalize(prefix + paragraph.text + "　");
    if (
      paragraph.kind === "heading" &&
      buffer.length > 0 &&
      PAGE_CAPACITY - buffer.length < characters.length + ROWS
    ) {
      flush();
    }
    buffer.push(...characters);
    while (buffer.length >= PAGE_CAPACITY) {
      pages.push({
        type: "body",
        heading: runningHeading,
        content: buffer.splice(0, PAGE_CAPACITY)
      });
    }
  }
  flush();

  if (options.includeBack) {
    if ((pages.length + 1) % 2 === 0) pages.push({ type: "blank" });
    const backCharacters = verticalize(
      book.backMatter.map((paragraph) => `　　${paragraph}　`).join("")
    );
    const backCapacity = 14 * 40;
    while (backCharacters.length) {
      pages.push({
        type: "colophon",
        heading: "版權頁",
        content: backCharacters.splice(0, backCapacity)
      });
    }
  }
  return pages;
}

function addText(parent, text, fontName, size, x, y, options = {}) {
  const node = figma.createText();
  parent.appendChild(node);
  node.fontName = fontName;
  node.fontSize = size;
  node.characters = text;
  node.fills = [{ type: "SOLID", color: BLACK }];
  node.x = x;
  node.y = y;
  if (options.lineHeight) {
    node.lineHeight = { unit: "PIXELS", value: options.lineHeight };
  }
  if (options.width && options.height) {
    node.textAutoResize = "NONE";
    node.resize(options.width, options.height);
  } else {
    node.textAutoResize = "WIDTH_AND_HEIGHT";
  }
  if (options.align) node.textAlignHorizontal = options.align;
  node.name = options.name || "text";
  return node;
}

function addFolio(frame, pageNumber, fontName, pageW, pageH) {
  addText(
    frame,
    String(pageNumber),
    fontName,
    7.5,
    pageW / 2 - 10,
    pageH - 24,
    { width: 20, height: 12, align: "CENTER", name: "folio" }
  );
}

function makeFrame(section, pageNumber, pageW, pageH, startY) {
  const frame = figma.createFrame();
  section.appendChild(frame);
  frame.name = `P${String(pageNumber).padStart(3, "0")}`;
  frame.resize(pageW, pageH);
  frame.fills = [{ type: "SOLID", color: WHITE }];
  frame.clipsContent = true;
  const localIndex = pageNumber - 1;
  const spreadRow = Math.floor(localIndex / 2);
  const isOdd = pageNumber % 2 === 1;
  // 直排右翻：奇數頁在右、偶數頁在左
  frame.x = isOdd ? pageW + 24 : 0;
  frame.y = startY + spreadRow * (pageH + 72);
  return frame;
}

function placeCenteredPunct(parent, glyph, _fontName, _fontSize, cellX, cellY, cellW, cellH) {
  const name = PUNCT_NAME[glyph] || glyph;
  const fill = [{ type: "SOLID", color: BLACK }];
  const nodes = [];

  const period = () => {
    const r = Math.min(cellW, cellH) * 0.12;
    const el = figma.createEllipse();
    parent.appendChild(el);
    el.resize(r * 2, r * 2);
    el.x = cellX + cellW / 2 - r;
    el.y = cellY + cellH / 2 - r;
    el.fills = fill;
    el.name = name;
    nodes.push(el);
  };

  const comma = () => {
    const w = cellW * 0.16;
    const h = cellH * 0.32;
    const node = figma.createRectangle();
    parent.appendChild(node);
    node.resize(w, h);
    node.cornerRadius = w / 2;
    node.x = cellX + cellW / 2 - w / 2;
    node.y = cellY + cellH / 2 - h / 2;
    node.fills = fill;
    node.name = name;
    nodes.push(node);
  };

  const colon = () => {
    const r = Math.min(cellW, cellH) * 0.095;
    const gap = cellH * 0.15;
    for (const sign of [-1, 1]) {
      const el = figma.createEllipse();
      parent.appendChild(el);
      el.resize(r * 2, r * 2);
      el.x = cellX + cellW / 2 - r;
      el.y = cellY + cellH / 2 - r + sign * gap;
      el.fills = fill;
      el.name = name;
      nodes.push(el);
    }
  };

  const bang = () => {
    const barW = cellW * 0.14;
    const barH = cellH * 0.42;
    const bar = figma.createRectangle();
    parent.appendChild(bar);
    bar.resize(barW, barH);
    bar.cornerRadius = barW / 2;
    bar.x = cellX + cellW / 2 - barW / 2;
    bar.y = cellY + cellH * 0.18;
    bar.fills = fill;
    bar.name = name;
    nodes.push(bar);
    const r = Math.min(cellW, cellH) * 0.09;
    const el = figma.createEllipse();
    parent.appendChild(el);
    el.resize(r * 2, r * 2);
    el.x = cellX + cellW / 2 - r;
    el.y = cellY + cellH * 0.72;
    el.fills = fill;
    el.name = name;
    nodes.push(el);
  };

  if (name === "︒") period();
  else if (name === "︐" || name === "︑") comma();
  else if (name === "︓") colon();
  else if (name === "︔") {
    const r = Math.min(cellW, cellH) * 0.09;
    const el = figma.createEllipse();
    parent.appendChild(el);
    el.resize(r * 2, r * 2);
    el.x = cellX + cellW / 2 - r;
    el.y = cellY + cellH * 0.32 - r;
    el.fills = fill;
    el.name = name;
    nodes.push(el);
    comma();
    nodes[nodes.length - 1].y = cellY + cellH * 0.55;
  } else if (name === "︕" || name === "︖") bang();
  else period();

  return nodes[0];
}

function renderBody(frame, page, pageNumber, fonts, pageW, pageH) {
  const isOdd = pageNumber % 2 === 1;
  const outer = 15 * PT_PER_MM;
  const inner = 18 * PT_PER_MM;
  const top = 18 * PT_PER_MM;
  const fontSize = 10.5;
  const lineHeight = 14.7;
  const columnPitch = 21.55;
  const colWidth = 13.125;
  const rightMargin = isOdd ? outer : inner;
  const rightEdge = pageW - rightMargin - colWidth;
  for (let column = 0; column < COLS; column += 1) {
    const characters = page.content.slice(column * ROWS, (column + 1) * ROWS);
    if (!characters.length) continue;
    const colX = rightEdge - column * columnPitch;
    const lines = [];
    for (let row = 0; row < characters.length; row += 1) {
      const character = characters[row];
      if (CENTER_PUNCT.has(character)) {
        const glyph = VERTICAL_FORMS[character] || character;
        // Direct page child — no 標點層 wrapper
        placeCenteredPunct(
          frame,
          glyph,
          fonts.regular,
          fontSize,
          colX,
          top + row * lineHeight,
          colWidth,
          lineHeight
        );
        lines.push("　");
      } else {
        lines.push(character);
      }
    }

    addText(frame, lines.join("\n"), fonts.regular, fontSize, colX, top, {
      lineHeight,
      width: colWidth,
      height: ROWS * lineHeight + 2,
      align: "CENTER",
      name: `正文 ${column + 1}`
    });
  }
  addFolio(frame, pageNumber, fonts.regular, pageW, pageH);
}

function renderOpener(frame, page, pageNumber, fonts, pageW, pageH) {
  const characters = verticalize(page.heading);
  const chunks = [];
  while (characters.length) chunks.push(characters.splice(0, 18));
  const startX = pageW - 105;
  for (let index = 0; index < chunks.length; index += 1) {
    addText(
      frame,
      chunks[index].join("\n"),
      fonts.bold,
      page.level === "volume" ? 18 : 15,
      startX - index * 37,
      82,
      {
        lineHeight: page.level === "volume" ? 27 : 23,
        width: 28,
        height: 490,
        align: "CENTER",
        name: "opener"
      }
    );
  }
  const rule = figma.createRectangle();
  frame.appendChild(rule);
  rule.name = "rule";
  rule.resize(0.7, 230);
  rule.x = startX + 45;
  rule.y = 96;
  rule.fills = [{ type: "SOLID", color: BLACK }];
  addFolio(frame, pageNumber, fonts.regular, pageW, pageH);
}

function renderHalfTitle(frame, book, fonts, pageW) {
  addText(
    frame,
    verticalize(book.title).join("\n"),
    fonts.bold,
    22,
    pageW - 138,
    128,
    { lineHeight: 34, width: 34, height: 330, align: "CENTER", name: "half-title" }
  );
}

function renderTitle(frame, book, fonts, pageW) {
  addText(
    frame,
    verticalize(book.title).join("\n"),
    fonts.bold,
    28,
    pageW - 145,
    92,
    { lineHeight: 42, width: 42, height: 380, align: "CENTER", name: "title" }
  );
  addText(
    frame,
    verticalize(`${book.series}　${book.author} 編著`).join("\n"),
    fonts.regular,
    10,
    pageW - 210,
    160,
    { lineHeight: 16, width: 18, height: 320, align: "CENTER", name: "title-meta" }
  );
}

function renderColophon(frame, page, pageNumber, fonts, pageW, pageH) {
  const rows = 40;
  const columns = 14;
  const fontSize = 7.5;
  const lineHeight = 12.2;
  const pitch = 16.5;
  const rightEdge = pageW - 48;
  for (let column = 0; column < columns; column += 1) {
    const characters = page.content.slice(column * rows, (column + 1) * rows);
    if (!characters.length) continue;
    addText(
      frame,
      characters.join("\n"),
      fonts.regular,
      fontSize,
      rightEdge - column * pitch,
      48,
      {
        lineHeight,
        width: 11,
        height: rows * lineHeight + 2,
        align: "CENTER",
        name: `colophon-${column + 1}`
      }
    );
  }
  addFolio(frame, pageNumber, fonts.regular, pageW, pageH);
}

function selectParagraphs(book, scope) {
  if (scope === "sample") {
    return {
      paragraphs: book.paragraphs.slice(0, 80),
      includeFront: true,
      includeBack: false,
      runningHeading: "樣本"
    };
  }
  if (scope === "front") {
    const firstVolume = book.paragraphs.findIndex((item) => item.kind === "volume");
    return {
      paragraphs: book.paragraphs.slice(0, firstVolume === -1 ? 120 : firstVolume),
      includeFront: true,
      includeBack: false,
      runningHeading: "總目錄"
    };
  }
  if (scope === "back") {
    return {
      paragraphs: [],
      includeFront: false,
      includeBack: true,
      runningHeading: "版權頁"
    };
  }
  if (scope.startsWith("volume:")) {
    const title = scope.slice("volume:".length);
    const start = book.paragraphs.findIndex(
      (item) => item.kind === "volume" && item.text === title
    );
    if (start === -1) throw new Error(`找不到卷：${title}`);
    let end = book.paragraphs.findIndex(
      (item, index) => index > start && item.kind === "volume"
    );
    if (end === -1) end = book.paragraphs.length;
    return {
      paragraphs: book.paragraphs.slice(start, end),
      includeFront: false,
      includeBack: false,
      runningHeading: title
    };
  }
  return {
    paragraphs: book.paragraphs,
    includeFront: true,
    includeBack: true,
    runningHeading: "總目錄"
  };
}

async function generateBook(message) {
  const book = message.book;
  if (!book || !Array.isArray(book.paragraphs)) {
    throw new Error("書稿資料無效。請先載入 book-data.json。");
  }

  const targetName = (message.targetName || "book3 page").trim();
  const targetPage =
    figma.root.children.find(
      (page) =>
        page.type === "PAGE" &&
        page.name.toLowerCase() === targetName.toLowerCase()
    ) || figma.currentPage;
  await figma.setCurrentPageAsync(targetPage);

  const sectionName = `${GENERATED_SECTION_NAME} / ${message.scopeLabel || message.scope}`;
  const existing = targetPage.children.find(
    (node) => node.type === "SECTION" && node.name === sectionName
  );
  if (existing && message.replace) existing.remove();

  const available = await figma.listAvailableFontsAsync();
  const fonts = chooseFonts(available);
  await Promise.all([
    figma.loadFontAsync(fonts.regular),
    fonts.bold.family === fonts.regular.family &&
    fonts.bold.style === fonts.regular.style
      ? Promise.resolve()
      : figma.loadFontAsync(fonts.bold)
  ]);

  let maxX = 0;
  let maxY = 0;
  for (const child of targetPage.children) {
    maxX = Math.max(maxX, child.x + child.width);
    maxY = Math.max(maxY, child.y + child.height);
  }

  const section = figma.createSection();
  targetPage.appendChild(section);
  section.name = sectionName;
  section.x = maxX + 200;
  section.y = 0;

  const selection = selectParagraphs(book, message.scope);
  const pages = splitRange(book, selection.paragraphs, selection);
  const { width: pageW, height: pageH } = pageSize(book);
  const startPageNumber = Number(message.startPageNumber) || 1;

  for (let index = 0; index < pages.length; index += 1) {
    const page = pages[index];
    const pageNumber = startPageNumber + index;
    const frame = makeFrame(section, pageNumber, pageW, pageH, 0);
    if (page.type === "body") renderBody(frame, page, pageNumber, fonts, pageW, pageH);
    if (page.type === "opener") {
      renderOpener(frame, page, pageNumber, fonts, pageW, pageH);
    }
    if (page.type === "half-title") renderHalfTitle(frame, book, fonts, pageW);
    if (page.type === "title") renderTitle(frame, book, fonts, pageW);
    if (page.type === "colophon") {
      renderColophon(frame, page, pageNumber, fonts, pageW, pageH);
    }
    if (index % 4 === 0 || index === pages.length - 1) {
      figma.ui.postMessage({
        type: "progress",
        current: index + 1,
        total: pages.length
      });
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  }

  figma.viewport.scrollAndZoomIntoView([section]);
  figma.currentPage.selection = [section];
  figma.ui.postMessage({
    type: "done",
    pages: pages.length,
    font: `${fonts.regular.family} ${fonts.regular.style}`,
    targetPage: targetPage.name,
    sectionName
  });
}

figma.ui.onmessage = async (message) => {
  if (message.type === "close") {
    figma.closePlugin();
    return;
  }
  if (message.type === "list-volumes") {
    const book = message.book;
    const volumes = (book?.paragraphs || [])
      .filter((item) => item.kind === "volume")
      .map((item) => item.text);
    figma.ui.postMessage({ type: "volumes", volumes });
    return;
  }
  if (message.type !== "generate") return;
  try {
    await generateBook(message);
  } catch (error) {
    figma.ui.postMessage({
      type: "error",
      message: error instanceof Error ? error.message : String(error)
    });
  }
};
