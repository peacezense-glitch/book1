/**
 * Vertical typesetting metrics for Figma (Test Book 5).
 *
 * 行距 (column pitch) = cp 21.55, NOT glyph width cw.
 * 標點: 全形符號（，。：；！？、）寫在正文欄內（ebook / SEO 可搜尋）；
 * textAlign H+V = CENTER；無獨立標點層、無向量替代。
 * 括號等仍用直式呈現形（﹁﹂︽︾）。
 *
 * TB5 layout (vs TB4):
 * - 修正左右 margin 不對稱：訂口＋外側＋正文寬 = 成品寬
 * - bindingMm 21：訂口略大於外側
 * - outerMm ~20：由 pageW − textBlock − binding 推得（約 20 mm）
 * - topMm 22 / rows 36；spreadGapMm 6；openerTopMm 22
 * - 外側卷題「第X卷」與卷名之間約 0.5 cm
 * - 外側卷題＋阿拉伯數字頁碼；版權頁橫排；書名獨立頁單線
 * - 對頁命名：對頁1、對頁2…
 */
module.exports = {
  rows: 36,
  cols: 15,
  cw: 13.125,
  cp: 21.55,
  lh: 14.7,
  fs: 10.5,
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
  edition: "test-book-5",
};
