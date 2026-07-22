#!/usr/bin/env node
/**
 * Reference metrics for Figma vertical render of《歸源手鏡》.
 *
 * In vertical setting, 行距 = distance between columns = columnPitch (cp),
 * NOT the glyph cell width (cw). Mixing these up makes the page look cramped.
 *
 *   cw (字幅)  = 13.125
 *   cp (行距)  = 21.55   ← place columns on this pitch
 *   lh (字距)  = 14.7    ← within-column leading for 10.5pt body
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
};
