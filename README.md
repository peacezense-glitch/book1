# 《歸源手鏡》書籍製作

本倉庫保存兩份原始 DOCX，以及可在 Figma Desktop 本機執行的直排書籍
Plugin。任何電腦只要取得這個 GitHub 倉庫，都能重新生成同一版本的書稿。

## 規格

- 成品尺寸：152 × 230 mm
- 文字方向：繁體中文直排、由右至左
- 內頁印刷：純黑文字、白底
- 正文：15 欄 × 每欄 32 字
- 裝訂邊留白：18 mm；外側留白：15 mm
- 內容包括半書名頁、書名頁、目錄、篇章頁、正文及版權尾頁

Figma 畫框使用 72 pt/in 的印刷比例，尺寸為約
`430.866 × 651.969` Figma units；匯出 PDF 後應為 152 × 230 mm。

## 在 Figma 生成書稿

1. 下載或 clone 本倉庫。
2. 用 Figma Desktop 開啟 `Book` 檔案。
3. 選擇 **Plugins → Development → Import plugin from manifest…**。
4. 選擇 `figma-plugin/manifest.json`。
5. 執行 **歸源手鏡・直排書籍生成器**。
6. 頁面名稱保留為 `book3 page`，按「生成完整內頁」。

Plugin 會建立名為 `歸源手鏡・內頁（Plugin 生成）` 的 Section。再次生成時，
預設只會替換這個 Section，不會刪除頁面上的其他設計。

生成完整書稿時會建立二百多個頁面畫框及數千個直排文字欄，請保持 Figma
開啟直至進度完成。Plugin 會優先使用 `Noto Serif TC` 或
`Source Han Serif TC`；如果電腦沒有這些字體，會自動選擇其他可用字體。

## DOCX 更新後重建 Plugin

Plugin 已把書稿及尾頁圖片內嵌，執行時不需要網絡。修改 DOCX 後，在倉庫根目錄
執行：

```bash
python3 tools/build_figma_plugin.py
```

這會更新：

- `figma-plugin/book-data.json`
- `figma-plugin/code.js`

請把 DOCX 與上述生成檔案一起提交到 GitHub，確保不同電腦使用同一版本。

## 印刷 PDF

1. 在 Figma 選取所有 `P001`、`P002`…頁面畫框。
2. 按頁碼順序匯出 PDF。
3. 在 Acrobat 或印前工具確認頁面尺寸是 152 × 230 mm、字體已嵌入。
4. 本版本內頁沒有出血圖；如印刷廠要求裁切線或 3 mm 出血，應按印刷廠的
   拼版規格處理，不要直接放大正文頁面。

EPUB 電子書應由 DOCX／結構化書稿另外生成，避免從 Figma PDF 反向轉換而失去
章節、搜尋及可調字級功能。
