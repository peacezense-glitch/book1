# 《歸源手鏡》書籍製作

本倉庫保存兩份原始 DOCX，以及可在 Figma Desktop 本機執行的直排書籍
Plugin。任何電腦只要取得這個 GitHub 倉庫，都能重新生成同一版本的書稿。

## 規格

- 成品尺寸：152 × 230 mm
- 文字方向：繁體中文直排、由右至左
- 內頁印刷：純黑文字、白底
- 正文：15 欄 × 每欄 32 字
- 裝訂邊留白：18 mm；外側留白：15 mm

## 在 Figma 生成書稿

Plugin 本體只有約 20KB，書稿資料放在 `data/book-data.json`，避免出現
`unable to write resource to disk`。

### 方法 A：直接匯入（推薦）

1. Clone／下載本倉庫。
2. 用 Figma Desktop 開啟 `Book`，進入 `book3 page`。
3. **Plugins → Development → Import plugin from manifest…**
4. 選擇 `figma-plugin/manifest.json`
5. 執行 **Guiyuan Vertical Book**
6. 載入書稿：
   - 本機選擇 `data/book-data.json`，或
   - 按「從 GitHub 載入書稿」
7. 先選「樣本」生成，確認後再分卷生成

### 方法 B：便攜 ZIP（路徑有中文／匯入失敗時）

1. 解壓 `figma-plugin/guiyuan-plugin-portable.zip` 到純英文路徑，例如
   `~/Desktop/guiyuan-plugin/`
2. 從該資料夾匯入 `manifest.json`
3. 書稿仍用倉庫裡的 `data/book-data.json`，或按「從 GitHub 載入書稿」

### 若仍出現 unable to write resource to disk

1. 改用方法 B 的純英文路徑
2. 完全關閉 Figma 後重開，再重新 Import
3. 確認匯入資料夾內只有 `manifest.json`、`code.js`、`ui.html` 三個小檔
4. 不要把整個 Git 倉庫根目錄當成 Plugin 資料夾匯入

## DOCX 更新後重建書稿資料

```bash
python3 tools/build_figma_plugin.py
```

這會更新 `data/book-data.json`。請把 DOCX 與這個 JSON 一起提交到 GitHub。

## 印刷 PDF

1. 在 Figma 選取 `P001`、`P002`…頁面畫框
2. 按頁碼順序匯出 PDF
3. 確認成品為 152 × 230 mm、字體已嵌入、內容為黑白

EPUB 應由 DOCX／結構化書稿另外生成，不要從 Figma PDF 反向轉換。
