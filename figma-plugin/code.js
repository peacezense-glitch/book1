const PT_PER_MM = 72 / 25.4;
const ROWS = 36;
const COLS = 15;
const PAGE_CAPACITY = ROWS * COLS;
const BINDING_MM = 21;
const OUTER_MM = 20; // nominal; exact outer derived from pageW − textBlock − binding
const TOP_MM = 22; // align body / 大標頭 with independent title leaf
const BOTTOM_MM = 16;
const SPREAD_GAP_MM = 6;
const OPENER_TOP_MM = 22; // align with independent title leaf
const RUNNING_HEAD_VOL_GAP_MM = 5; // 0.5 cm between 第X卷 and 卷名
const COLUMN_PITCH = 21.55;
const COL_WIDTH = 13.125;
const BLACK = { r: 0, g: 0, b: 0 };
const WHITE = { r: 1, g: 1, b: 1 };
const GENERATED_SECTION_NAME = "Guiyuan Interior";
const CN_DIGITS = "〇一二三四五六七八九";

const VERTICAL_FORMS = {
  // Match Test Book 2 / ebook: keep ，。、：；！？ as fullwidth symbols (SEO-searchable).
  // Only brackets/dashes/ellipsis get vertical presentation forms.
  "「": "﹁", "」": "﹂", "『": "﹃",
  "』": "﹄", "（": "︵", "）": "︶", "【": "︻", "】": "︼",
  "《": "︽", "》": "︾", "〈": "︿", "〉": "﹀", "〔": "︹",
  "〕": "︺", "［": "﹇", "］": "﹈", "—": "︱", "─": "︱",
  "…": "︙", "·": "・"
};

figma.showUI(__html__, { width: 400, height: 620, themeColors: true });

function chineseDigits(n) {
  return String(n)
    .split("")
    .map((d) => CN_DIGITS[Number(d)] || d)
    .join("");
}

function volumeRunningTitle(text) {
  const clean = String(text).replace(/[\u3000\s]+/g, "");
  const vol = clean.match(/^(第.+?卷)([^：:]*?)[：:].+$/);
  if (vol) return vol[1] + vol[2];
  const app = clean.match(/^(附錄[一二三四])/);
  if (app) return app[1];
  return clean;
}

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
    pages.push({
      type: "colophon",
      heading: "版權頁",
      matter: book.backMatter || []
    });
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
  if (options.align) {
    node.textAlignHorizontal = options.align;
  }
  if (options.alignVertical) {
    node.textAlignVertical = options.alignVertical;
  } else if (options.align === "CENTER") {
    node.textAlignVertical = "CENTER";
  }
  node.name = options.name || "text";
  return node;
}

function pageSideMargins(pageW) {
  // Exact pair: binding + outer + textBlock = page width (fixes TB4 asymmetry).
  const textBlockW = (COLS - 1) * COLUMN_PITCH + COL_WIDTH;
  const inner = BINDING_MM * PT_PER_MM;
  const outer = pageW - textBlockW - inner;
  return { inner, outer, textBlockW };
}

function splitRunningHead(title) {
  const clean = String(title || "");
  const vol = clean.match(/^(第[一二三四五六七八九十百千零〇\d]+卷)(.+)$/);
  if (vol && vol[2]) return [vol[1], vol[2]];
  const app = clean.match(/^(附錄[一二三四])(.+)$/);
  if (app && app[2]) return [app[1], app[2]];
  return [clean, ""];
}

function addRunningHead(frame, heading, pageNumber, pageW, pageH, fontName) {
  const isOdd = pageNumber % 2 === 1;
  const { inner, outer, textBlockW } = pageSideMargins(pageW);
  const gapBody = 5 * PT_PER_MM; // 0.5 cm from body
  const gapFolio = 10 * PT_PER_MM; // 1 cm between 卷題 and 頁碼
  const volGap = RUNNING_HEAD_VOL_GAP_MM * PT_PER_MM; // 0.5 cm inside 卷題
  const lineHeight = 11;
  const width = 10;
  const [head, sub] = splitRunningHead(heading);
  const folio = chineseDigits(pageNumber);
  const headChars = Array.from(head).filter(Boolean);
  const subChars = Array.from(sub).filter(Boolean);
  const folioChars = Array.from(folio);
  const headH = Math.max(headChars.length, 1) * lineHeight + 2;
  const subH = subChars.length ? subChars.length * lineHeight + 2 : 0;
  const titleBlockH = headH + (subH ? volGap + subH : 0);
  const folioH = Math.max(folioChars.length, 1) * lineHeight + 2;
  // Gap straddles page midline so both sides share the same horizontal band.
  const titleY = pageH / 2 - gapFolio / 2 - titleBlockH;
  const folioY = pageH / 2 + gapFolio / 2;
  let x;
  if (isOdd) {
    // Outer (right) margin: sit gapBody outside the text block.
    x = pageW - outer + gapBody;
  } else {
    // Outer (left) margin: sit gapBody left of the text block.
    x = pageW - inner - textBlockW - gapBody - width;
  }
  if (headChars.length) {
    addText(frame, headChars.join("\n"), fontName, 8, x, titleY, {
      lineHeight,
      width,
      height: headH,
      align: "CENTER",
      name: "卷題"
    });
  }
  if (subChars.length) {
    addText(frame, subChars.join("\n"), fontName, 8, x, titleY + headH + volGap, {
      lineHeight,
      width,
      height: subH,
      align: "CENTER",
      name: "卷題名"
    });
  }
  addText(frame, folioChars.join("\n"), fontName, 8, x, folioY, {
    lineHeight,
    width,
    height: folioH,
    align: "CENTER",
    name: "頁碼"
  });
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
  const gap = SPREAD_GAP_MM * PT_PER_MM;
  // 直排右翻：奇數頁在右、偶數頁在左；左右略分開
  frame.x = isOdd ? pageW + gap : 0;
  frame.y = startY + spreadRow * (pageH + 72);
  return frame;
}

function renderBody(frame, page, pageNumber, fonts, pageW, pageH) {
  const isOdd = pageNumber % 2 === 1;
  const { inner, outer } = pageSideMargins(pageW);
  const top = TOP_MM * PT_PER_MM;
  const fontSize = 10.5;
  const lineHeight = 14.7;
  const columnPitch = COLUMN_PITCH;
  const colWidth = COL_WIDTH;
  const rightMargin = isOdd ? outer : inner;
  const rightEdge = pageW - rightMargin - colWidth;
  // Test Book 2 recipe: fullwidth punct stays inline in the column;
  // textAlign H+V CENTER centers each cell (ebook/SEO: real text symbols only).
  for (let column = 0; column < COLS; column += 1) {
    const characters = page.content.slice(column * ROWS, (column + 1) * ROWS);
    if (!characters.length) continue;
    const colX = rightEdge - column * columnPitch;
    const lines = characters.map((character) => VERTICAL_FORMS[character] || character);
    addText(frame, lines.join("\n"), fonts.regular, fontSize, colX, top, {
      lineHeight,
      width: colWidth,
      height: lines.length * lineHeight + 2,
      align: "CENTER",
      name: `正文 ${column + 1}`
    });
  }
  addRunningHead(
    frame,
    page.heading || "正文",
    pageNumber,
    pageW,
    pageH,
    fonts.regular
  );
}

function renderOpener(frame, page, pageNumber, fonts, pageW, pageH) {
  const lines =
    Array.isArray(page.lines) && page.lines.length
      ? page.lines
      : (() => {
          const characters = verticalize(page.heading);
          const chunks = [];
          while (characters.length) chunks.push(characters.splice(0, 18).join(""));
          return chunks;
        })();
  // Chapter openers match volume size (18); 自序/major stays slightly smaller.
  const fs = page.level === "major" ? 16 : 18;
  const lh = page.level === "major" ? 23 : 27;
  const openerTop = OPENER_TOP_MM * PT_PER_MM;
  const colW = 28;
  const pitch = 37;
  const n = Math.max(lines.length, 1);
  const groupW = colW + (n - 1) * pitch;
  // Horizontally center the opener group on the page.
  const rightmostX = pageW / 2 + groupW / 2 - colW;
  let tallest = 0;
  for (let index = 0; index < lines.length; index += 1) {
    let chars = Array.from(String(lines[index]));
    if (!chars.length) continue;
    let colon = null;
    const last = chars[chars.length - 1];
    if (last === "：" || last === ":" || last === "︓") {
      colon = "：";
      chars = chars.slice(0, -1);
    }
    const height = chars.length * lh + 2;
    tallest = Math.max(tallest, height + (colon ? lh : 0));
    const colX = rightmostX - index * pitch;
    if (chars.length) {
      addText(frame, chars.join("\n"), fonts.bold, fs, colX, openerTop, {
        lineHeight: lh,
        width: colW,
        height,
        align: "CENTER",
        alignVertical: "TOP",
        name: "opener"
      });
    }
    if (colon) {
      addText(
        frame,
        colon,
        fonts.bold,
        fs,
        colX,
        openerTop + chars.length * lh,
        {
          lineHeight: lh,
          width: colW,
          height: lh + 2,
          align: "CENTER",
          alignVertical: "CENTER",
          name: "opener-colon"
        }
      );
    }
  }
  const rule = figma.createRectangle();
  frame.appendChild(rule);
  rule.name = "rule";
  rule.resize(0.7, Math.max(tallest, 220));
  rule.x = rightmostX + colW + 14;
  rule.y = openerTop;
  rule.fills = [{ type: "SOLID", color: BLACK }];
  addRunningHead(
    frame,
    volumeRunningTitle(page.heading),
    pageNumber,
    pageW,
    pageH,
    fonts.regular
  );
}

function renderTitleCard(frame, page, pageNumber, fonts, pageW, pageH) {
  // Unique post-preface book title leaf — single rule, vertically centered.
  const title = String(page.title || page.tx || "");
  const subtitle = String(page.sub || page.subtitle || "");
  const titleFs = 18;
  const titleLh = 28;
  const subFs = 11;
  const subLh = 18;
  const colW = 28;
  const pitch = 40;
  const subGap = 18;

  let titleCols = [];
  const colonIdx = Math.max(title.indexOf("："), title.indexOf(":"));
  if (colonIdx > 0) {
    titleCols = [title.slice(0, colonIdx), title.slice(colonIdx + 1)].filter(Boolean);
  } else {
    titleCols = title ? [title] : [];
  }
  const groupW =
    colW +
    Math.max(titleCols.length - 1, 0) * pitch +
    (subtitle ? pitch + subGap : 0);
  const rightmostX = pageW / 2 + groupW / 2 - colW;

  // Measure heights to vertically center the block.
  const titleHeights = titleCols.map((col) => {
    const chars = Array.from(col);
    const colonExtra = colonIdx > 0 && col === titleCols[0] ? titleLh : 0;
    return chars.length * titleLh + colonExtra + 4;
  });
  const subH = subtitle ? Array.from(subtitle).length * subLh + 4 : 0;
  const blockH = Math.max(...titleHeights, subH || 0, 220);
  const top = (pageH - blockH) / 2 - 8;

  // Single vertical rule to the right of the title group.
  const rule = figma.createRectangle();
  frame.appendChild(rule);
  rule.name = "title-rule";
  rule.resize(0.7, blockH);
  rule.x = rightmostX + colW + 18;
  rule.y = top;
  rule.fills = [{ type: "SOLID", color: BLACK }];

  for (let i = 0; i < titleCols.length; i += 1) {
    let chars = Array.from(titleCols[i]);
    const colX = rightmostX - i * pitch;
    const isLead = i === 0 && colonIdx > 0;
    addText(frame, chars.join("\n"), fonts.bold, titleFs, colX, top, {
      lineHeight: titleLh,
      width: colW,
      height: chars.length * titleLh + 4,
      align: "CENTER",
      alignVertical: "TOP",
      name: "書名"
    });
    if (isLead) {
      addText(frame, "：", fonts.bold, titleFs, colX, top + chars.length * titleLh, {
        lineHeight: titleLh,
        width: colW,
        height: titleLh + 2,
        align: "CENTER",
        alignVertical: "CENTER",
        name: "書名-colon"
      });
    }
  }
  if (subtitle) {
    const chars = Array.from(subtitle);
    const subX = rightmostX - titleCols.length * pitch - subGap;
    addText(frame, chars.join("\n"), fonts.regular, subFs, subX, top + 48, {
      lineHeight: subLh,
      width: colW,
      height: chars.length * subLh + 4,
      align: "CENTER",
      alignVertical: "TOP",
      name: "副題"
    });
  }
  // Folio only — no 卷題 on this dedicated leaf.
  addRunningHead(frame, "", pageNumber, pageW, pageH, fonts.regular);
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
  // Traditional: only the copyright page is horizontal (English-heavy).
  const matter = Array.isArray(page.matter) ? page.matter : [];
  const marginX = 28;
  const contentW = pageW - marginX * 2;
  let y = 36;
  const title = matter[0] || "《歸源手鏡》";
  addText(frame, title, fonts.bold, 16, marginX, y, {
    width: contentW,
    height: 28,
    align: "CENTER",
    name: "colophon-title"
  });
  y += 36;
  const metaLines = matter.slice(1, 8);
  for (const line of metaLines) {
    addText(frame, line, fonts.regular, 9, marginX, y, {
      width: contentW,
      height: 16,
      align: "LEFT",
      name: "colophon-meta"
    });
    y += 15;
  }
  y += 10;
  const centerLines = matter.slice(8, 18);
  for (const line of centerLines) {
    addText(frame, line, fonts.regular, 8.5, marginX, y, {
      width: contentW,
      height: 14,
      align: "LEFT",
      name: "colophon-center"
    });
    y += 13;
  }
  y += 8;
  const pubLines = matter.slice(18);
  const legalStart = pubLines.findIndex(
    (line) =>
      /All Right Reserved|版權所有|免責聲明|Nothing may be reprinted/i.test(line)
  );
  const beforeLegal = legalStart === -1 ? pubLines : pubLines.slice(0, legalStart);
  const legal = legalStart === -1 ? [] : pubLines.slice(legalStart);
  for (const line of beforeLegal) {
    if (/Youtube|華玉講堂\s*課程$/.test(line)) continue;
    addText(frame, line, fonts.regular, 8.5, marginX, y, {
      width: contentW,
      height: 14,
      align: "LEFT",
      name: "colophon-pub"
    });
    y += 13;
    if (/掃瞄二維碼|掃描二維碼|掃描二維|掃瞄二維/.test(line)) {
      y += 4;
      y = placeColophonQr(frame, page.qr, fonts, marginX, y, contentW);
      y += 8;
    }
  }
  // If invitation line missing, still place QR before legal.
  if (!frame.findOne((n) => n.name === "colophon-qr")) {
    y += 4;
    y = placeColophonQr(frame, page.qr, fonts, marginX, y, contentW);
    y += 8;
  }
  const legalHeights = legal.map((line) => (line.length > 60 ? 36 : 18));
  const legalBlock = legalHeights.reduce((sum, h) => sum + h + 2, 0);
  const bottomPad = 22 * PT_PER_MM; // keep disclaimer clear of the trim
  y = Math.min(y + 6, pageH - bottomPad - legalBlock);
  for (let i = 0; i < legal.length; i += 1) {
    const h = legalHeights[i];
    addText(frame, legal[i], fonts.regular, 7, marginX, y, {
      width: contentW,
      height: h,
      align: "LEFT",
      name: "colophon-legal"
    });
    y += h + 2;
  }
}

function placeColophonQr(frame, qr, fonts, marginX, y, contentW) {
  const data = qr || {};
  const title = data.title || "講堂課程登記表";
  const url = data.url || "www.daohk.com";
  const matrix = Array.isArray(data.matrix) ? data.matrix : [];
  addText(frame, title, fonts.bold, 10, marginX, y, {
    width: contentW,
    height: 14,
    align: "CENTER",
    name: "colophon-qr-title"
  });
  y += 16;
  const qrSize = 72; // ~25.4 mm
  const qrX = marginX + (contentW - qrSize) / 2;
  if (matrix.length) {
    const n = matrix.length;
    const cell = qrSize / n;
    const parts = [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${qrSize}" height="${qrSize}" shape-rendering="crispEdges">`,
      `<rect width="100%" height="100%" fill="#ffffff"/>`
    ];
    for (let r = 0; r < n; r += 1) {
      for (let c = 0; c < n; c += 1) {
        if (!matrix[r][c]) continue;
        parts.push(
          `<rect x="${(c * cell).toFixed(3)}" y="${(r * cell).toFixed(3)}" width="${cell.toFixed(3)}" height="${cell.toFixed(3)}" fill="#000000"/>`
        );
      }
    }
    parts.push("</svg>");
    const node = figma.createNodeFromSvg(parts.join(""));
    frame.appendChild(node);
    node.name = "colophon-qr";
    node.x = qrX;
    node.y = y;
  } else {
    const placeholder = figma.createRectangle();
    frame.appendChild(placeholder);
    placeholder.name = "colophon-qr";
    placeholder.resize(qrSize, qrSize);
    placeholder.x = qrX;
    placeholder.y = y;
    placeholder.fills = [];
    placeholder.strokes = [{ type: "SOLID", color: BLACK }];
    placeholder.strokeWeight = 1;
  }
  y += qrSize + 6;
  addText(frame, url, fonts.regular, 8, marginX, y, {
    width: contentW,
    height: 12,
    align: "CENTER",
    name: "colophon-qr-url"
  });
  return y + 14;
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
    if (page.type === "title_card") {
      renderTitleCard(frame, page, pageNumber, fonts, pageW, pageH);
    }
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
