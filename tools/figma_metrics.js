/**
 * Vertical typesetting metrics for Figma (Test Book 8).
 *
 * 行距 (column pitch) = cp 21.55, NOT glyph width cw.
 * 標點: 全形符號（，。：；！？、）寫在正文欄內（ebook / SEO 可搜尋）；
 * textAlign H+V = CENTER；無獨立標點層、無向量替代。
 * 括號等仍用直式呈現形（﹁﹂︽︾）。
 *
 * TB8 layout (vs TB7):
 * - body 10.5→10 pt；行距 14.7→14；字框 cw 13.125→12.5
 * - 標題／頁眉等比縮小（×10/10.5，半點取整）
 * - 斷行／開新頁／甚字／引文退格／編號步驟等規則不變
 * - bindingMm 21；outer ≈20；topMm 22 / rows 36
 */
module.exports = {
  rows: 36,
  cols: 15,
  cw: 12.5,
  cp: 21.55,
  lh: 12.6,
  fs: 10,
  bindingMm: 21,
  // Companion outer is derived at render time so left+right are exact.
  outerMm: 20,
  topMm: 22,
  bottomMm: 16,
  spreadGapMm: 6,
  openerTopMm: 22,
  runningHeadVolGapMm: 5,
  trimMm: { w: 152, h: 230 },
  textAlignHorizontal: "CENTER",
  textAlignVertical: "CENTER",
  punctMode: "inline-fullwidth-symbols",
  runningHead: "volume-outer",
  colophon: "horizontal",
  edition: "test-book-8",
};
