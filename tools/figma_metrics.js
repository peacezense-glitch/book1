/**
 * Vertical typesetting metrics for Figma (match Test Book 2).
 *
 * 行距 (column pitch) = cp 21.55, NOT glyph width cw.
 * 標點: 全形符號（，。：；！？、）寫在正文欄內（ebook / SEO 可搜尋）；
 * textAlign H+V = CENTER；無獨立標點層、無向量替代。
 * 括號等仍用直式呈現形（﹁﹂︽︾…）。
 */
module.exports = {
  rows: 32,
  cols: 15,
  cw: 13.125,
  cp: 21.55,
  lh: 14.7,
  fs: 10.5,
  bindingMm: 18,
  outerMm: 15,
  trimMm: { w: 152, h: 230 },
  textAlignHorizontal: "CENTER",
  textAlignVertical: "CENTER",
  punctMode: "inline-fullwidth-symbols",
};
