# 《歸源手鏡》書籍製作

本倉庫保存兩份原始 DOCX、結構化書稿資料，以及可在 Figma Desktop 本機執行的直排書籍 Plugin。任何電腦只要取得這個 GitHub 倉庫，都能重新生成同一版本的書稿。

## 目前 Figma 輸出

- 帳號：`uxuimno@gmail.com`（Pro）
- 檔案：[Button-Test](https://www.figma.com/design/MiTnf3APyMXeGIH9Jgkek7/Button-Test?node-id=473-2)
- **主排版頁：`Test Book 8`**
- 舊版參考：`Test Book 7`、`Test Book 6`、`Test Book 5`、`Test Book 4`、`Test Book 3`、`Test Book 2`、`Test Book`
- 已生成：對頁全冊；目錄在前、正文、**橫排版權頁**在後；**無填充空白頁**
- 規格：152 × 230 mm、繁體直排、黑白、Noto Serif TC
- **裝訂：直排右翻** — 右頁為奇數（第一頁），左頁為偶數（第二頁）
- **正文：10 pt／行距 12.6**（較前版 14 減 10%）；15 欄 × **36** 字
- **頁面邊距**：訂口 **21 mm**、外側 **≈20 mm**（訂口＋外側＋正文寬＝成品寬）、上 **22 mm**
- **封面**：頁首獨立「封面」畫框（152×230 mm），不計入內文頁碼
- **對頁命名**：Figma 畫框 `對頁1`、`對頁2`…
- **頁碼**：外側直排 **阿拉伯數字**（1、2、12…）
- **書眉**：左右**外側**直排 **卷題＋阿拉伯數字頁碼**（7.5 pt）；弟子序書眉為短題 **「序」**
- **正文用字**：一律「甚」（「甚麼／為甚麼」）；僅「鳩摩羅什」保留「什」
- **多欄引文**：對話標點﹁﹂區塊中，第二欄起退一格，與首欄正文對齊
- **編號步驟**（如「1．生疑：」）：粗體、頂端對齊
- **插圖**：九天玄女（自序）、呂祖（第五卷）、四人圖（附錄一前）；**封面**與**華玉講堂宣傳頁**保留全彩（ebook＋彩色印刷）
- **版權頁**：欄位對齊；研究所／講堂聯絡縮進；雙 QR（講堂課程登記表卡＋Youtube）＋短標
- MCP 排版：載入 `book-data-carrier.png` **一次排完全書**
- ebook／分頁計畫：`data/book-data.json`、`data/pages-plan.json`、`book-data-carrier.png`

## 規格

- 成品尺寸：152 × 230 mm
- 文字方向：繁體中文直排、由右至左
- 內頁印刷：正文純黑文字、白底；**封面／宣傳頁保留全彩**（ebook 與彩色印刷）
- 正文：15 欄 × 每欄 36 字（Test Book 8；正文 10 pt／行距 14）
- 裝訂邊留白：21 mm；外側留白：≈20 mm（與正文寬合計剛好 152 mm）；上邊：22 mm

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

成品 **152 × 230 mm**；印刷檔另加 **四周 3 mm 出血**（Media **158 × 236 mm**），並轉 **CMYK**。

```bash
# 葉面已匯出至 exports/ebook-pages/ 後：
python3 tools/merge_ebook_pdf.py
# → exports/歸源手鏡-ebook.pdf（RGB／螢幕／ebook）

python3 tools/build_print_pdf.py
# → exports/歸源手鏡-print-cmyk-bleed3mm.pdf（CMYK＋3mm 出血）
```

- 封面／宣傳頁／插圖頁：內容放大填滿出血
- 其餘內文頁：置中，出血為白邊
- 確認字體已嵌入；正文為黑字白底

## Ebook PDF（Figma 版面）

從 **Test Book 8** 逐葉匯出並合併（封面＋P001–P318；封面為更新後圖檔）：

```bash
# 1) 在 Figma 取得葉面清單 → data/ebook-export-manifest.json（agent 可自動生成）
# 2) 逐葉 download_assets (pdf, scale 2) → exports/ebook-pages/
python3 tools/merge_ebook_pdf.py
# → exports/歸源手鏡-ebook.pdf
```

EPUB 應由 DOCX／結構化書稿另外生成，不要從 Figma PDF 反向轉換。
