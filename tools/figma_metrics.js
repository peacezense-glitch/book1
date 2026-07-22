/**
 * Vertical typesetting metrics for Figma (Test Book 4).
 *
 * 行距 (column pitch) = cp 21.55, NOT glyph width cw.
 * 標點: 全形符號（，。：；！？、）寫在正文欄內（ebook / SEO 可搜尋）；
 * textAlign H+V = CENTER；無獨立標點層、無向量替代。
 * 括號等仍用直式呈現形（﹁﹂︽︾）。
 *
 * TB4 layout (vs TB3):
 * - bindingMm 22：訂口加大，避免釘裝覆蓋
 * - outerMm 13：外側留給卷題／頁碼
 * - topMm 22 / rows 36：正文／大標頭高度對齊獨立書名葉
 * - spreadGapMm 6：見開き左右頁略分開
 * - openerTopMm 22：大標題高度對齊獨立書名葉
 * - 外側卷題「第X卷」與卷名之間約 0.5 cm
 * - 外側卷題＋中文數字頁碼；版權頁橫排；書名獨立頁單線
 */
module.exports = {
  rows: 36,
  cols: 15,
  cw: 13.125,
  cp: 21.55,
  lh: 14.7,
  fs: 10.5,
  bindingMm: 22,
  outerMm: 13,
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
};
