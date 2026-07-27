# 《歸源手鏡》書籍製作

本倉庫保存兩份原始 DOCX、結構化書稿資料，以及可在 Figma Desktop 本機執行的直排書籍 Plugin。任何電腦只要取得這個 GitHub 倉庫，都能重新生成同一版本的書稿。

## 目前 Figma 輸出

- 帳號：`uxuimno@gmail.com`（Pro）
- 檔案：[Button-Test](https://www.figma.com/design/MiTnf3APyMXeGIH9Jgkek7/Button-Test?node-id=473-2)
- **主排版頁：`Test Book 5`**（node `473:2`；左右 margin 對稱修正）
- 舊版參考：`Test Book 4`、`Test Book 3`、`Test Book 2`、`Test Book`
- 已生成：對頁全冊；目錄在前、正文、**橫排版權頁**在後；**無填充空白頁**
- 規格：152 × 230 mm、繁體直排、黑白、Noto Serif TC
- **裝訂：直排右翻** — 右頁為奇數（第一頁），左頁為偶數（第二頁）
- **正文：10.5 pt／行距 14.7**；15 欄 × **36** 字；篇章／卷標題更大
- **頁面邊距（TB5）**：訂口 **21 mm**、外側 **≈20 mm**（訂口＋外側＋正文寬＝成品寬，修正 TB4 左右不對稱）、上 **22 mm**
- **頁碼**：外側直排 **羅馬數字**（I、II、XII…）
- **對頁命名**：Figma 畫框 `對頁1`、`對頁2`…（原「見開き 001」）
- **書眉**：左右**外側**直排 **卷題＋羅馬數字頁碼**（如 `第一卷`／`立基` 間約 0.5 cm）
- 標點：對齊 **Test Book 2** — 全形符號（，。：；！？、）**寫在正文欄內**（ebook／SEO 可搜尋文字）；`textAlign` H+V = CENTER；**無標點層、無向量替代**。括號等仍用直式呈現形（﹁﹂︽︾）
- **版權頁**：依傳統**僅此頁橫排**（英文較多），其餘全書直排
- 小標題／提示：**前留一空欄，後直接接正文**
- **大標題断行**：章＝`第X章｜題｜｜｜副題`（破折號貼題名）；卷＝`第X卷｜題︓｜副題`
- **目錄換頁**：同一卷（含附錄塊）盡量整組同頁，不拆到半卷（如第五卷整組在後頁）
- 目錄：對齊原 Test Book — **卷／自序／附錄粗體頂格**；**章節細體＋頂端縮進**；無 `·`；字號 **11 pt**
- **語意排版**（不印稿面標籤）：「副標題：」等標籤剝除，只排真正內容
- 層級：卷／章 opener **18**／自序 16；小標題 Bold 11；提示／功課標 Bold 11；次級標 Bold 10.5＋縮進；正文 Regular 10.5
- 自序落款：「宏泓道者謹識」**粗體 12**、「丙午年長夏」細體，**置於欄底**；其後書名 Bold 12、副題 Regular 11（無「副標題」二字）
- **版權頁 QR**：講堂課程登記表 → `www.daohk.com`（黑白矩陣，印於掃碼提示下方）
- MCP 排版：載入 `book-data-carrier.png` **一次排完全書**
- ebook／分頁計畫：`data/book-data.json`、`data/pages-plan.json`、`book-data-carrier.png`

## 規格

- 成品尺寸：152 × 230 mm
- 文字方向：繁體中文直排、由右至左
- 內頁印刷：純黑文字、白底
- 正文：15 欄 × 每欄 36 字（Test Book 5）
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

1. 在 Figma 選取對頁／頁面畫框
2. 按頁碼順序匯出 PDF（右奇左偶）
3. 確認成品為 152 × 230 mm、字體已嵌入、內容為黑白

EPUB 應由 DOCX／結構化書稿另外生成，不要從 Figma PDF 反向轉換。
