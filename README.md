# 《歸源手鏡》書籍製作

本倉庫保存兩份原始 DOCX、結構化書稿資料，以及可在 Figma Desktop 本機執行的直排書籍 Plugin。任何電腦只要取得這個 GitHub 倉庫，都能重新生成同一版本的書稿。

## 目前 Figma 輸出

- 帳號：`uxuimno@gmail.com`（Pro）
- 檔案：[Button-Test](https://www.figma.com/design/MiTnf3APyMXeGIH9Jgkek7/Button-Test?node-id=103-4020)
- **主排版頁：`Test Book 3`**
- 舊版參考：`Test Book`、`Test Book 2`
- 已生成：**P001–P328**（164 見開き），目錄在前、正文、版權頁在後；**無填充空白頁**
- 規格：152 × 230 mm、繁體直排、黑白、Noto Serif TC
- **裝訂：直排右翻** — 右頁為奇數（第一頁），左頁為偶數（第二頁）
- **正文：10.5 pt／行距 14.7**；15 欄 × 32 字；篇章／卷標題更大
- 標點：直接寫在正文欄（無獨立標點 layer）
- 小標題／副標題：**前留一空欄，後直接接正文**
- 目錄：對齊原 Test Book — **卷／自序／附錄粗體頂格**；**章節細體＋頂端縮進**；無 `·`
- MCP 排版：載入 `book-data-carrier.png` **一次排完全書**
- ebook／分頁計畫：`data/book-data.json`、`data/pages-plan.json`、`book-data-carrier.png`

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
2. 用 Figma Desktop 開啟目標檔案。
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
python3 tools/paginate_book.py
```

這會更新 `data/book-data.json`、`data/pages-plan.json` 與 `book-data-carrier.png`。請把 DOCX 與這些產物一起提交到 GitHub。

## 印刷 PDF

1. 在 Figma 選取見開き／頁面畫框
2. 按頁碼順序匯出 PDF（右奇左偶）
3. 確認成品為 152 × 230 mm、字體已嵌入、內容為黑白

EPUB 應由 DOCX／結構化書稿另外生成，不要從 Figma PDF 反向轉換。
