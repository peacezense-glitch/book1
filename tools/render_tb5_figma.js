const HASH = "4972db9146dc4ef2d169ea2c4113877386428022";
const COVER_HASH = "e30e2a3507acebc4b110935682888cf7c04a11fa";
const PAGE_NAME = "Test Book 5";
const PAGE = figma.root.children.find((p) => p.name === PAGE_NAME);
if (!PAGE) throw new Error("missing Test Book 5");
await figma.setCurrentPageAsync(PAGE);
for (const child of [...PAGE.children]) child.remove();
await figma.loadFontAsync({ family: "Noto Serif TC", style: "Regular" });
await figma.loadFontAsync({ family: "Noto Serif TC", style: "Bold" });
const REG = { family: "Noto Serif TC", style: "Regular" };
const BOLD = { family: "Noto Serif TC", style: "Bold" };
const PT = 72 / 25.4;
const PAGE_W = 152 * PT;
const PAGE_H = 230 * PT;
const FS = 10.5, LH = 14.7, CP = 21.55, CW = 13.125, COLS = 15;
const INNER = 21 * PT, TOP = 22 * PT;
const GAP_BODY = 5 * PT, GAP_FOLIO = 10 * PT;
const SPREAD_GAP = 6 * PT;
const OPENER_TOP = 22 * PT;
const VOL_GAP = 5 * PT;
const BLACK = { r: 0, g: 0, b: 0 }, WHITE = { r: 1, g: 1, b: 1 };
const BOLD_STYLES = new Set(["1", "2", "5", "7", "9", "b"]);
const STYLE_FS = { "0": 10.5, "1": 11, "2": 11, "5": 11, "6": 11, "7": 12, "8": 10.5, "9": 12, a: 11, b: 10.5 };
function pageSideMargins() {
  const textBlockW = (COLS - 1) * CP + CW;
  const inner = INNER;
  const outer = PAGE_W - textBlockW - inner;
  return { inner, outer, textBlockW };
}
function u32(b, i) { return ((b[i] << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3]) >>> 0; }
function utf8Decode(bytes) {
  let out = "", i = 0;
  while (i < bytes.length) {
    const c = bytes[i++];
    if (c < 0x80) out += String.fromCharCode(c);
    else if (c < 0xe0) out += String.fromCharCode(((c & 0x1f) << 6) | (bytes[i++] & 0x3f));
    else if (c < 0xf0) {
      const c2 = bytes[i++], c3 = bytes[i++];
      out += String.fromCharCode(((c & 0x0f) << 12) | ((c2 & 0x3f) << 6) | (c3 & 0x3f));
    } else {
      const c2 = bytes[i++], c3 = bytes[i++], c4 = bytes[i++];
      let cp = ((c & 0x07) << 18) | ((c2 & 0x3f) << 12) | ((c3 & 0x3f) << 6) | (c4 & 0x3f);
      cp -= 0x10000;
      out += String.fromCharCode(0xd800 + (cp >> 10), 0xdc00 + (cp & 0x3ff));
    }
  }
  return out;
}
const image = figma.getImageByHash(HASH);
const bytes = await image.getBytesAsync();
let pos = 8; const collected = [];
while (pos + 8 <= bytes.length) {
  const len = u32(bytes, pos);
  const tag = String.fromCharCode(bytes[pos + 4], bytes[pos + 5], bytes[pos + 6], bytes[pos + 7]);
  const start = pos + 8;
  const body = bytes.slice(start, start + len);
  pos = start + len + 4;
  if (tag === "bkDt") for (let i = 0; i < body.length; i++) collected.push(body[i]);
  if (tag === "IEND") break;
}
const plan = JSON.parse(utf8Decode(Uint8Array.from(collected)));
const pages = plan.pages;
const asset = figma.createRectangle();
PAGE.appendChild(asset);
asset.name = "BOOK_DATA_ASSET";
asset.resize(1, 1); asset.x = -2000; asset.y = -2000;
asset.fills = [{ type: "IMAGE", imageHash: HASH, scaleMode: "FILL" }];
// Front cover (outside interior pagination).
const cover = figma.createFrame();
PAGE.appendChild(cover);
cover.name = "封面";
cover.resize(PAGE_W, PAGE_H);
cover.x = 80;
cover.y = 80;
cover.clipsContent = true;
cover.fills = [{ type: "IMAGE", imageHash: COVER_HASH, scaleMode: "FILL" }];
const SPREAD_START_Y = 80 + PAGE_H + 72;
function ensureSpread(si) {
  let sp = PAGE.children.find((c) => c.name === `對頁${si + 1}`);
  if (!sp) {
    sp = figma.createFrame();
    PAGE.appendChild(sp);
    sp.name = `對頁${si + 1}`;
    sp.resize(PAGE_W * 2 + SPREAD_GAP, PAGE_H);
    sp.fills = [];
    sp.clipsContent = false;
    sp.x = 80;
    sp.y = SPREAD_START_Y + si * (PAGE_H + 72);
  }
  return sp;
}
function splitRunningHead(title) {
  const clean = String(title || "");
  const vol = clean.match(/^(第[一二三四五六七八九十百千零〇\d]+卷)(.+)$/);
  if (vol && vol[2]) return [vol[1], vol[2]];
  const app = clean.match(/^(附錄[一二三四])(.+)$/);
  if (app && app[2]) return [app[1], app[2]];
  return [clean, ""];
}
function addRunningHead(fr, page) {
  const isOdd = page.n % 2 === 1;
  const { inner, outer, textBlockW } = pageSideMargins();
  const [head, sub] = splitRunningHead(String(page.vh || ""));
  const folio = String(page.fo || "");
  const lineHeight = 11, width = 10;
  const headChars = Array.from(head).filter(Boolean);
  const subChars = Array.from(sub).filter(Boolean);
  const folioChars = Array.from(folio);
  const headH = Math.max(headChars.length, 1) * lineHeight + 2;
  const subH = subChars.length ? subChars.length * lineHeight + 2 : 0;
  const titleBlockH = headH + (subH ? VOL_GAP + subH : 0);
  const folioH = Math.max(folioChars.length, 1) * lineHeight + 2;
  const titleY = PAGE_H / 2 - GAP_FOLIO / 2 - titleBlockH;
  const folioY = PAGE_H / 2 + GAP_FOLIO / 2;
  const x = isOdd ? PAGE_W - outer + GAP_BODY : PAGE_W - inner - textBlockW - GAP_BODY - width;
  if (headChars.length) {
    const node = figma.createText();
    fr.appendChild(node);
    node.fontName = REG; node.fontSize = 8;
    node.characters = headChars.join("\n");
    node.fills = [{ type: "SOLID", color: BLACK }];
    node.textAlignHorizontal = "CENTER"; node.textAlignVertical = "CENTER";
    node.lineHeight = { unit: "PIXELS", value: lineHeight };
    node.textAutoResize = "NONE"; node.resize(width, headH);
    node.x = x; node.y = titleY; node.name = "卷題";
  }
  if (subChars.length) {
    const node = figma.createText();
    fr.appendChild(node);
    node.fontName = REG; node.fontSize = 8;
    node.characters = subChars.join("\n");
    node.fills = [{ type: "SOLID", color: BLACK }];
    node.textAlignHorizontal = "CENTER"; node.textAlignVertical = "CENTER";
    node.lineHeight = { unit: "PIXELS", value: lineHeight };
    node.textAutoResize = "NONE"; node.resize(width, subH);
    node.x = x; node.y = titleY + headH + VOL_GAP; node.name = "卷題名";
  }
  if (folioChars.length) {
    const node = figma.createText();
    fr.appendChild(node);
    node.fontName = REG; node.fontSize = 8;
    node.characters = folioChars.join("\n");
    node.fills = [{ type: "SOLID", color: BLACK }];
    node.textAlignHorizontal = "CENTER"; node.textAlignVertical = "CENTER";
    node.lineHeight = { unit: "PIXELS", value: lineHeight };
    node.textAutoResize = "NONE"; node.resize(width, folioH);
    node.x = x; node.y = folioY; node.name = "頁碼";
  }
}
function styleName(s0) {
  return ({ "1": "小標題", "2": "提示", "5": "目錄卷", "6": "目錄章", "7": "落款", "8": "落款年月", "9": "書名", a: "副題", b: "次級標" })[s0] || "正文";
}
function renderCols(fr, cols, isOdd) {
  const { inner, outer } = pageSideMargins();
  const rightMargin = isOdd ? outer : inner;
  const rightEdge = PAGE_W - rightMargin - CW;
  for (const col of cols) {
    const chars = Array.from(col.c);
    if (!chars.length) continue;
    const st = col.s.length === 1 ? col.s.repeat(chars.length) : col.s;
    const indent = col.d || 0;
    let i = 0;
    while (i < chars.length) {
      const s0 = st[i] || "0";
      let j = i + 1;
      while (j < chars.length && (st[j] || "0") === s0) j++;
      const node = figma.createText();
      fr.appendChild(node);
      node.fontName = BOLD_STYLES.has(s0) ? BOLD : REG;
      node.fontSize = col.fs || STYLE_FS[s0] || FS;
      node.characters = chars.slice(i, j).join("\n");
      node.fills = [{ type: "SOLID", color: BLACK }];
      node.textAlignHorizontal = "CENTER"; node.textAlignVertical = "CENTER";
      node.lineHeight = { unit: "PIXELS", value: LH };
      node.textAutoResize = "NONE";
      node.resize(CW, (j - i) * LH + 2);
      node.x = rightEdge - col.i * CP;
      node.y = TOP + (indent + i) * LH;
      node.name = styleName(s0);
      i = j;
    }
  }
}
function renderOpener(fr, page) {
  const lines = page.ln && page.ln.length ? page.ln : [String(page.tx || "")];
  // Chapter openers match volume size (18); 自序/major stays slightly smaller.
  const fs = page.lv === "major" ? 16 : 18;
  const lh = page.lv === "major" ? 23 : 27;
  const colW = 28, pitch = 37;
  const n = Math.max(lines.length, 1);
  const groupW = colW + (n - 1) * pitch;
  const rightmostX = PAGE_W / 2 + groupW / 2 - colW;
  let tallest = 0;
  for (let i = 0; i < lines.length; i++) {
    let chars = Array.from(String(lines[i]));
    if (!chars.length) continue;
    let colon = null;
    const last = chars[chars.length - 1];
    if (last === "：" || last === ":" || last === "︓") { colon = "："; chars = chars.slice(0, -1); }
    const h = chars.length * lh + 2;
    tallest = Math.max(tallest, h + (colon ? lh : 0));
    const colX = rightmostX - i * pitch;
    if (chars.length) {
      const node = figma.createText();
      fr.appendChild(node);
      node.fontName = BOLD; node.fontSize = fs;
      node.characters = chars.join("\n");
      node.fills = [{ type: "SOLID", color: BLACK }];
      node.textAlignHorizontal = "CENTER"; node.textAlignVertical = "TOP";
      node.lineHeight = { unit: "PIXELS", value: lh };
      node.textAutoResize = "NONE"; node.resize(colW, h);
      node.x = colX; node.y = OPENER_TOP; node.name = "opener";
    }
    if (colon) {
      const node = figma.createText();
      fr.appendChild(node);
      node.fontName = BOLD; node.fontSize = fs;
      node.characters = colon;
      node.fills = [{ type: "SOLID", color: BLACK }];
      node.textAlignHorizontal = "CENTER"; node.textAlignVertical = "CENTER";
      node.lineHeight = { unit: "PIXELS", value: lh };
      node.textAutoResize = "NONE"; node.resize(colW, lh + 2);
      node.x = colX; node.y = OPENER_TOP + chars.length * lh; node.name = "opener-colon";
    }
  }
  const rule = figma.createRectangle();
  fr.appendChild(rule);
  rule.name = "rule";
  rule.resize(0.7, Math.max(tallest, 220));
  rule.x = rightmostX + colW + 14;
  rule.y = OPENER_TOP;
  rule.fills = [{ type: "SOLID", color: BLACK }];
}
function renderTitleCard(fr, page) {
  const title = String(page.title || "");
  const subtitle = String(page.sub || "");
  const titleFs = 18, titleLh = 28, subFs = 11, subLh = 18;
  const colW = 28, pitch = 40, subGap = 18;
  let titleCols = [];
  const colonIdx = Math.max(title.indexOf("："), title.indexOf(":"));
  if (colonIdx > 0) titleCols = [title.slice(0, colonIdx), title.slice(colonIdx + 1)].filter(Boolean);
  else titleCols = title ? [title] : [];
  const groupW = colW + Math.max(titleCols.length - 1, 0) * pitch + (subtitle ? pitch + subGap : 0);
  const rightmostX = PAGE_W / 2 + groupW / 2 - colW;
  const titleHeights = titleCols.map((col, i) => {
    const chars = Array.from(col);
    const colonExtra = colonIdx > 0 && i === 0 ? titleLh : 0;
    return chars.length * titleLh + colonExtra + 4;
  });
  const subH = subtitle ? Array.from(subtitle).length * subLh + 4 : 0;
  const blockH = Math.max(...(titleHeights.length ? titleHeights : [0]), subH || 0, 220);
  const top = (PAGE_H - blockH) / 2 - 8;
  const rule = figma.createRectangle();
  fr.appendChild(rule);
  rule.name = "title-rule";
  rule.resize(0.7, blockH);
  rule.x = rightmostX + colW + 18;
  rule.y = top;
  rule.fills = [{ type: "SOLID", color: BLACK }];
  for (let i = 0; i < titleCols.length; i++) {
    const chars = Array.from(titleCols[i]);
    const colX = rightmostX - i * pitch;
    const node = figma.createText();
    fr.appendChild(node);
    node.fontName = BOLD; node.fontSize = titleFs;
    node.characters = chars.join("\n");
    node.fills = [{ type: "SOLID", color: BLACK }];
    node.textAlignHorizontal = "CENTER"; node.textAlignVertical = "TOP";
    node.lineHeight = { unit: "PIXELS", value: titleLh };
    node.textAutoResize = "NONE";
    node.resize(colW, chars.length * titleLh + 4);
    node.x = colX; node.y = top; node.name = "書名";
    if (i === 0 && colonIdx > 0) {
      const colon = figma.createText();
      fr.appendChild(colon);
      colon.fontName = BOLD; colon.fontSize = titleFs;
      colon.characters = "：";
      colon.fills = [{ type: "SOLID", color: BLACK }];
      colon.textAlignHorizontal = "CENTER"; colon.textAlignVertical = "CENTER";
      colon.lineHeight = { unit: "PIXELS", value: titleLh };
      colon.textAutoResize = "NONE";
      colon.resize(colW, titleLh + 2);
      colon.x = colX; colon.y = top + chars.length * titleLh; colon.name = "書名-colon";
    }
  }
  if (subtitle) {
    const chars = Array.from(subtitle);
    const node = figma.createText();
    fr.appendChild(node);
    node.fontName = REG; node.fontSize = subFs;
    node.characters = chars.join("\n");
    node.fills = [{ type: "SOLID", color: BLACK }];
    node.textAlignHorizontal = "CENTER"; node.textAlignVertical = "TOP";
    node.lineHeight = { unit: "PIXELS", value: subLh };
    node.textAutoResize = "NONE";
    node.resize(colW, chars.length * subLh + 4);
    node.x = rightmostX - titleCols.length * pitch - subGap;
    node.y = top + 48; node.name = "副題";
  }
}
function addHText(fr, text, font, size, x, y, w, h, align, name) {
  const node = figma.createText();
  fr.appendChild(node);
  node.fontName = font; node.fontSize = size; node.characters = text;
  node.fills = [{ type: "SOLID", color: BLACK }];
  node.textAlignHorizontal = align; node.textAutoResize = "NONE";
  node.resize(w, h); node.x = x; node.y = y; node.name = name;
}
function placeColophonQr(fr, qr, marginX, y, contentW) {
  const data = qr || {};
  const title = data.title || "講堂課程登記表";
  const url = data.url || "www.daohk.com";
  const matrix = Array.isArray(data.matrix) ? data.matrix : [];
  addHText(fr, title, BOLD, 10, marginX, y, contentW, 14, "CENTER", "colophon-qr-title");
  y += 14; // title then QR flush (blank line is above this block)
  const qrSize = 72;
  const qrX = marginX + (contentW - qrSize) / 2;
  if (matrix.length) {
    const n = matrix.length;
    const cell = qrSize / n;
    const parts = [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${qrSize}" height="${qrSize}" shape-rendering="crispEdges">`,
      `<rect width="100%" height="100%" fill="#ffffff"/>`
    ];
    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        if (!matrix[r][c]) continue;
        parts.push(
          `<rect x="${(c * cell).toFixed(3)}" y="${(r * cell).toFixed(3)}" width="${cell.toFixed(3)}" height="${cell.toFixed(3)}" fill="#000000"/>`
        );
      }
    }
    parts.push("</svg>");
    const node = figma.createNodeFromSvg(parts.join(""));
    fr.appendChild(node);
    node.name = "colophon-qr";
    node.x = qrX;
    node.y = y;
  } else {
    const placeholder = figma.createRectangle();
    fr.appendChild(placeholder);
    placeholder.name = "colophon-qr";
    placeholder.resize(qrSize, qrSize);
    placeholder.x = qrX;
    placeholder.y = y;
    placeholder.fills = [];
    placeholder.strokes = [{ type: "SOLID", color: BLACK }];
    placeholder.strokeWeight = 1;
  }
  y += qrSize + 6;
  addHText(fr, url, REG, 8, marginX, y, contentW, 12, "CENTER", "colophon-qr-url");
  return y + 14;
}
function renderColophon(fr, page) {
  const marginX = 26, bottomPad = 22 * PT, contentW = PAGE_W - marginX * 2;
  let y = 28;
  addHText(fr, `《${page.title || "歸源手鏡"}》`, BOLD, 14, marginX, y, contentW, 22, "CENTER", "colophon-title");
  y += 24;
  if (page.series) { addHText(fr, `— ${page.series} —`, REG, 8.5, marginX, y, contentW, 12, "CENTER", "colophon-series"); y += 14; }
  const matter = page.matter || [];
  let i = 0;
  if (matter[0] && matter[0].includes("歸源手鏡")) i = 1;
  const metaEnd = Math.min(i + 7, matter.length);
  for (; i < metaEnd; i++) { addHText(fr, matter[i], REG, 8.5, marginX, y, contentW, 12, "LEFT", "colophon-meta"); y += 12; }
  y += 6;
  addHText(fr, "Center", BOLD, 8.5, marginX, y, contentW, 12, "LEFT", "colophon-center-label"); y += 13;
  const centerEnd = Math.min(i + 10, matter.length);
  for (; i < centerEnd; i++) { addHText(fr, matter[i], REG, 7.5, marginX, y, contentW, 11, "LEFT", "colophon-center"); y += 11; }
  y += 6;
  const rest = matter.slice(i);
  const legalStart = rest.findIndex((line) => /All Right Reserved|版權所有|免責聲明|Nothing may be reprinted/i.test(line));
  const beforeLegal = legalStart === -1 ? rest : rest.slice(0, legalStart);
  const legal = legalStart === -1 ? [] : rest.slice(legalStart);
  let qrPlaced = false;
  for (const line of beforeLegal) {
    if (/Youtube|華玉講堂\s*課程$/.test(line)) continue;
    addHText(fr, line, REG, 8, marginX, y, contentW, 12, "LEFT", "colophon-pub");
    y += 12;
    if (/掃瞄二維碼|掃描二維碼|掃描二維|掃瞄二維/.test(line)) {
      y += 14; // one blank line above QR block
      y = placeColophonQr(fr, page.qr, marginX, y, contentW);
      qrPlaced = true;
    }
  }
  if (!qrPlaced) {
    y += 14;
    y = placeColophonQr(fr, page.qr, marginX, y, contentW);
  }
  const legalHeights = legal.map((line) => (line.length > 60 ? 36 : 16));
  const legalBlock = legalHeights.reduce((sum, h) => sum + h + 2, 0);
  y = Math.min(y + 6, PAGE_H - bottomPad - legalBlock);
  for (let k = 0; k < legal.length; k++) {
    addHText(fr, legal[k], REG, 6.5, marginX, y, contentW, legalHeights[k], "LEFT", "colophon-legal");
    y += legalHeights[k] + 2;
  }
}
const created = [];
let blankPages = 0, titleCards = 0, colophonPages = 0;
for (const page of pages) {
  if (page.t === "b") { blankPages++; continue; }
  const n = page.n;
  const si = Math.floor((n - 1) / 2);
  const sp = ensureSpread(si);
  const isOdd = n % 2 === 1;
  const fr = figma.createFrame();
  sp.appendChild(fr);
  fr.name = `P${String(n).padStart(3, "0")}`;
  fr.resize(PAGE_W, PAGE_H);
  fr.fills = [{ type: "SOLID", color: WHITE }];
  fr.clipsContent = true;
  fr.x = isOdd ? PAGE_W + SPREAD_GAP : 0;
  fr.y = 0;
  if (page.t === "o") renderOpener(fr, page);
  else if (page.t === "p") renderCols(fr, page.cols || [], isOdd);
  else if (page.t === "tc") { renderTitleCard(fr, page); titleCards++; }
  else if (page.t === "c") { renderColophon(fr, page); colophonPages++; }
  if (page.t !== "c") addRunningHead(fr, page);
  created.push(fr.id);
}
const sample = PAGE.children.find((c) => c.name === "對頁1");
let layout = null;
if (sample) {
  await sample.screenshot({ scale: 0.55 });
  const m = pageSideMargins();
  layout = {
    marginsMm: {
      binding: +(INNER / PT).toFixed(2),
      outer: +(m.outer / PT).toFixed(2),
      textBlock: +(m.textBlockW / PT).toFixed(2),
      sum: +((INNER + m.outer + m.textBlockW) / PT).toFixed(2)
    },
    pages: sample.children.map((fr) => {
      const texts = fr.findAll((t) => t.type === "TEXT" && t.name === "正文");
      const xs = texts.map((t) => t.x);
      const left = xs.length ? Math.min(...xs) : null;
      const right = xs.length ? Math.max(...xs) + CW : null;
      return {
        name: fr.name,
        x: Math.round(fr.x),
        leftMm: left == null ? null : +(left / PT).toFixed(2),
        rightMm: right == null ? null : +((PAGE_W - right) / PT).toFixed(2)
      };
    })
  };
}
return {
  created: created.length,
  blankSkipped: blankPages,
  titleCards,
  colophonPages,
  spreads: PAGE.children.filter((c) => c.name.startsWith("對頁")).length,
  layout,
  pageId: PAGE.id,
  createdNodeIds: created.slice(0, 8)
};
