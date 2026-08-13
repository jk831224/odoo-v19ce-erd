# Odoo v19 CE ERD 全景圖

一張可縮放、可平移的 ERD 畫布，把 Odoo 19 社群版的資料結構逐塊畫進去。所有欄位、關聯、約束都從跑著的 `odoo-dev-19` 資料庫實查，不是憑記憶或版本印象寫的。

目標是回答規劃層級的問題：這個需求會落在哪些 model、它們怎麼接、刪一筆會連動到什麼、匯入要照什麼順序。

## 檔案

| 檔案 | 用途 |
|---|---|
| `global-view.html` | **主檔，所有改動改這裡。**從 jsdelivr 載入 mermaid，需要網路 |
| `global-view.offline.html` | 產物，mermaid 內嵌，完全離線。**不要直接編輯**，下次組裝會覆蓋 |
| `sale-chain.html` | 銷售鏈（`sale.order` → `stock.picking` → `account.move`），尚未併入全景圖 |
| `build-offline.py` | 組裝腳本 |
| `vendor/mermaid.min.js` | mermaid 11 UMD bundle，3.4 MB，0 個動態 import 所以離線可用 |
| `archive/contacts-static.html` | 第一版的靜態長頁，已被畫布版取代，留著對照 |

日常看圖用 `global-view.offline.html`，雙擊即可，不需要伺服器也不需要網路。

## 怎麼看

| 動作 | 操作 |
|---|---|
| 平移 | 兩指滑動，或直接拖曳畫布 |
| 縮放 | pinch，或 `⌘` + 滾輪（以游標為中心） |
| 局部放大 | 雙擊該處 |
| 適配全圖 / 實際大小 | `0` / `1` |
| 開關說明面板 | `I`，`Esc` 關閉 |
| 找特定實體 | 說明面板第一區「實體索引」，點擊飛到定位 |

滑過任一實體會浮出它的關鍵事實：現有筆數、必填欄位、要不要自己建、有什麼坑。**縮小到看不清框內文字時，hover 是主要的閱讀方式。**

## 目前涵蓋

24 個實體，兩塊。

**聯絡人（12）**：`res.partner` 為中心，加上 `res.country`、`res.country.state`、`res.city`、`res.partner.category` 與其 m2m 中介表、`res.partner.industry`、`res.users`、`res.company`、`res.partner.bank`、`account.payment.term`、`account.account`。

**商品主檔（12）**：`product.template` / `product.product` 雙層，加上 `product.category` 分類樹、`uom.uom`、`product.uom` 條碼表、`product.supplierinfo` 供應商價目，以及產生變體的四層屬性系統與兩張中介表。

**兩塊的接縫**：`product.supplierinfo.partner_id` → `res.partner`，`required` + `cascade`。這是商品與聯絡人唯一的直接連結。

## 資料來源

`odoo-dev-19` 資料庫的 `ir_model_fields` 與 PostgreSQL 系統表（`pg_constraint`、`information_schema.columns`）。查詢日期 **2026-08-13**，當時已安裝 74 個模組，含 `l10n_tw` 與 `base_vat`。

**這張圖反映的是這一套環境的模組組合。**裝不同的模組會得到不同的欄位集合——例如目前 `res.partner.bank` 上那個 `required` 的 `l10n_us_bank_account_type`，就是同時裝了 `l10n_us` 的副作用。

## 尚未涵蓋

採購鏈、庫存內部（`stock.quant`、`stock.location` 階層、補貨鏈）、會計側的對帳與稅務、價目表規則（`product.pricelist.item`）、商品標籤、製造、專案、人資，以及所有 `l10n_*` 在地化模組加上的欄位。

銷售鏈已經畫在 `sale-chain.html`，但還沒併進全景圖。

## 重建離線版

改完 `global-view.html` 之後：

```bash
python3 build-offline.py
```

腳本會內嵌 mermaid、移除 sourceMap 註解、跳脫 `</script>`，並檢查產出的檔案沒有任何外部引用。

## 已知限制

**Mermaid 的自動佈局有天花板，而且已經開始碰到。**目前 24 個實體，圖是 5093 × 3916。在 1440×900 螢幕上：

| 縮放 | 框內文字 | 看得到全圖的 |
|---|---|---|
| 20%（全圖適配） | 2.8px | 100% |
| 60% | 8.4px | 20% |
| 100% | 14px | 7% |

意思是全圖適配只能看結構輪廓，讀內容得放大。實體索引與 hover 卡就是為了補這一點。

另外 Mermaid 不支援手動定位，所以無法把「銷售放右邊、會計放下面」這種空間語意固定下來。已經出現長距離跨越的連線（例如 `product.uom` 被排到左下角，連到右側的 `product.product`）。實體再增加時，可能需要改成分層顯示或換成可手動佈局的格式——見 `CLAUDE.md` 的擴充規則。
