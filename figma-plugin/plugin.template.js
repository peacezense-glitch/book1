const BOOK = /*__BOOK_DATA__*/;

const PT_PER_MM = 72 / 25.4;
const PAGE_W = BOOK.trim.widthMm * PT_PER_MM;
const PAGE_H = BOOK.trim.heightMm * PT_PER_MM;
const ROWS = 32;
const COLS = 15;
const PAGE_CAPACITY = ROWS * COLS;
const BLACK = { r: 0, g: 0, b: 0 };
const WHITE = { r: 1, g: 1, b: 1 };
const GENERATED_SECTION_NAME = "歸源手鏡・內頁（Plugin 生成）";

const VERTICAL_FORMS = {
  "，": "︐", "、": "︑", "。": "︒", "：": "︓", "；": "︔",
  "！": "︕", "？": "︖", "「": "﹁", "」": "﹂", "『": "﹃",
  "』": "﹄", "（": "︵", "）": "︶", "【": "︻", "】": "︼",
  "《": "︽", "》": "︾", "〈": "︿", "〉": "﹀", "〔": "︹",
  "〕": "︺", "［": "﹇", "］": "﹈", "—": "︱", "─": "︱",
  "…": "︙", "·": "・"
};

figma.showUI(__html__, { width: 380, height: 560, themeColors: true });

function verticalize(text) {
  return Array.from(text.replace(/\s+/g, " "))
    .map((character) => VERTICAL_FORMS[character] || character);
}

function chooseFonts(available) {
  const fonts = available.map((entry) => entry.fontName);
  const regularPreferences = [
    ["Noto Serif TC", "Regular"],
    ["Source Han Serif TC", "Regular"],
    ["Noto Serif CJK TC", "Regular"],
    ["Songti TC", "Regular"],
    ["PMingLiU", "Regular"],
    ["Arial Unicode MS", "Regular"],
    ["Inter", "Regular"]
  ];
  const boldPreferences = [
    ["Noto Serif TC", "Bold"],
    ["Source Han Serif TC", "Bold"],
    ["Noto Serif CJK TC", "Bold"],
    ["Songti TC", "Bold"],
    ["PMingLiU", "Bold"],
    ["Inter", "Bold"]
  ];
  const find = (preferences) => {
    for (const [family, style] of preferences) {
      const exact = fonts.find(
        (font) => font.family === family && font.style === style
      );
      if (exact) return exact;
    }
    return null;
  };
  const regular = find(regularPreferences) || fonts[0];
  const bold = find(boldPreferences) || regular;
  if (!regular) throw new Error("Figma 找不到可用字體。");
  return { regular, bold };
}

function splitIntoPages() {
  const pages = [
    { type: "half-title", heading: BOOK.title },
    { type: "blank" },
    { type: "title", heading: BOOK.title },
    { type: "blank" }
  ];
  let buffer = [];
  let runningHeading = "總目錄";

  const flush = () => {
    while (buffer.length) {
      pages.push({
        type: "body",
        heading: runningHeading,
        content: buffer.splice(0, PAGE_CAPACITY)
      });
    }
  };

  for (const paragraph of BOOK.paragraphs) {
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

  if ((pages.length + 1) % 2 === 0) pages.push({ type: "blank" });
  const backCharacters = verticalize(
    BOOK.backMatter.map((paragraph) => `　　${paragraph}　`).join("")
  );
  const backCapacity = 14 * 40;
  while (backCharacters.length) {
    pages.push({
      type: "colophon",
      heading: "版權頁",
      content: backCharacters.splice(0, backCapacity),
      final: backCharacters.length === 0
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
  if (options.align) node.textAlignHorizontal = options.align;
  if (options.opacity !== undefined) node.opacity = options.opacity;
  node.name = options.name || "文字";
  return node;
}

function addFolio(frame, pageNumber, fontName) {
  const text = String(pageNumber);
  const folio = addText(
    frame, text, fontName, 7.5, PAGE_W / 2 - 10, PAGE_H - 24,
    { width: 20, height: 12, align: "CENTER", name: "頁碼" }
  );
  folio.letterSpacing = { unit: "PERCENT", value: 8 };
}

function makeFrame(section, pageNumber) {
  const frame = figma.createFrame();
  section.appendChild(frame);
  frame.name = `P${String(pageNumber).padStart(3, "0")}`;
  frame.resize(PAGE_W, PAGE_H);
  frame.fills = [{ type: "SOLID", color: WHITE }];
  frame.clipsContent = true;
  const spreadRow = Math.floor((pageNumber - 1) / 2);
  const isOdd = pageNumber % 2 === 1;
  frame.x = isOdd ? PAGE_W + 24 : 0;
  frame.y = spreadRow * (PAGE_H + 72);
  return frame;
}

function renderBody(frame, page, pageNumber, fonts) {
  const isOdd = pageNumber % 2 === 1;
  const outer = 15 * PT_PER_MM;
  const inner = 18 * PT_PER_MM;
  const top = 18 * PT_PER_MM;
  const fontSize = 10.5;
  const lineHeight = 15.8;
  const columnPitch = 20.2;
  const rightMargin = isOdd ? outer : inner;
  const rightEdge = PAGE_W - rightMargin - fontSize * 1.2;

  for (let column = 0; column < COLS; column += 1) {
    const characters = page.content.slice(column * ROWS, (column + 1) * ROWS);
    if (!characters.length) continue;
    addText(
      frame,
      characters.join("\n"),
      fonts.regular,
      fontSize,
      rightEdge - column * columnPitch,
      top,
      {
        lineHeight,
        width: fontSize * 1.45,
        height: ROWS * lineHeight + 2,
        align: "CENTER",
        name: `正文・第${column + 1}欄`
      }
    );
  }
  addFolio(frame, pageNumber, fonts.regular);
}

function renderOpener(frame, page, pageNumber, fonts) {
  const characters = verticalize(page.heading);
  const chunks = [];
  while (characters.length) chunks.push(characters.splice(0, 18));
  const startX = PAGE_W - 105;
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
        name: "篇章標題"
      }
    );
  }
  const rule = figma.createRectangle();
  frame.appendChild(rule);
  rule.name = "篇章分隔線";
  rule.resize(0.7, 230);
  rule.x = startX + 45;
  rule.y = 96;
  rule.fills = [{ type: "SOLID", color: BLACK }];
  addFolio(frame, pageNumber, fonts.regular);
}

function renderHalfTitle(frame, fonts) {
  addText(
    frame,
    verticalize(BOOK.title).join("\n"),
    fonts.bold,
    22,
    PAGE_W - 138,
    128,
    {
      lineHeight: 34,
      width: 34,
      height: 330,
      align: "CENTER",
      name: "半書名"
    }
  );
}

function renderTitle(frame, fonts) {
  addText(
    frame,
    verticalize(BOOK.title).join("\n"),
    fonts.bold,
    28,
    PAGE_W - 145,
    92,
    {
      lineHeight: 42,
      width: 42,
      height: 380,
      align: "CENTER",
      name: "書名"
    }
  );
  addText(
    frame,
    verticalize(`${BOOK.series}　${BOOK.author} 編著`).join("\n"),
    fonts.regular,
    10,
    PAGE_W - 210,
    160,
    {
      lineHeight: 16,
      width: 18,
      height: 320,
      align: "CENTER",
      name: "書名頁資料"
    }
  );
}

function bytesFromBase64(encoded) {
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function addBackMatterImages(frame) {
  const images = BOOK.backMatterImages.slice(-2);
  images.forEach((asset, index) => {
    const rectangle = figma.createRectangle();
    frame.appendChild(rectangle);
    rectangle.name = `尾頁圖片・${asset.name}`;
    rectangle.resize(62, 62);
    rectangle.x = 72 + index * 86;
    rectangle.y = PAGE_H - 108;
    const image = figma.createImage(bytesFromBase64(asset.base64));
    rectangle.fills = [{
      type: "IMAGE",
      imageHash: image.hash,
      scaleMode: "FIT",
      filters: { saturation: -1 }
    }];
  });
}

function renderColophon(frame, page, pageNumber, fonts) {
  const rows = 40;
  const columns = 14;
  const fontSize = 7.5;
  const lineHeight = 12.2;
  const pitch = 16.5;
  const rightEdge = PAGE_W - 48;
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
        name: `版權資料・第${column + 1}欄`
      }
    );
  }
  if (page.final) addBackMatterImages(frame);
  addFolio(frame, pageNumber, fonts.regular);
}

async function generateBook(options) {
  const targetName = (options.targetName || "book3 page").trim();
  const targetPage = figma.root.children.find(
    (page) => page.type === "PAGE" && page.name.toLowerCase() === targetName.toLowerCase()
  ) || figma.currentPage;
  await figma.setCurrentPageAsync(targetPage);

  const existing = targetPage.children.find(
    (node) => node.type === "SECTION" && node.name === GENERATED_SECTION_NAME
  );
  if (existing && options.replace) existing.remove();

  const available = await figma.listAvailableFontsAsync();
  const fonts = chooseFonts(available);
  await Promise.all([
    figma.loadFontAsync(fonts.regular),
    fonts.bold.family === fonts.regular.family && fonts.bold.style === fonts.regular.style
      ? Promise.resolve()
      : figma.loadFontAsync(fonts.bold)
  ]);

  let maxX = 0;
  for (const child of targetPage.children) {
    maxX = Math.max(maxX, child.x + child.width);
  }
  const section = figma.createSection();
  targetPage.appendChild(section);
  section.name = GENERATED_SECTION_NAME;
  section.x = maxX + 200;
  section.y = 0;

  const pages = splitIntoPages();
  for (let index = 0; index < pages.length; index += 1) {
    const page = pages[index];
    const pageNumber = index + 1;
    const frame = makeFrame(section, pageNumber);
    if (page.type === "body") renderBody(frame, page, pageNumber, fonts);
    if (page.type === "opener") renderOpener(frame, page, pageNumber, fonts);
    if (page.type === "half-title") renderHalfTitle(frame, fonts);
    if (page.type === "title") renderTitle(frame, fonts);
    if (page.type === "colophon") {
      renderColophon(frame, page, pageNumber, fonts);
    }
    if (index % 5 === 0 || index === pages.length - 1) {
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
    targetPage: targetPage.name
  });
}

figma.ui.onmessage = async (message) => {
  if (message.type === "close") {
    figma.closePlugin();
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
