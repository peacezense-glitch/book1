/**
 * Vertical typesetting metrics for Figma.
 *
 * 行距 (column pitch) = cp 21.55, NOT glyph width cw.
 * 標點: 格心向量符號（圓／豎條／雙點），直接掛在頁面下（不要標點層）。
 * 不用字型 ︐︒ — Noto 直式標點墨心偏隅，無法靠 align/optical 真正置中。
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
  punctMode: "vector-cell-center",
};
