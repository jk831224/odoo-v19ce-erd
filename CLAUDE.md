# Odoo v19 CE ERD 全景圖 — 工作規則

本檔是給在這個資料夾工作的 Claude 的指引。與 `~/.claude/CLAUDE.md`、`../CLAUDE.md`（Odoo 19 sandbox）並存，**不覆寫**它們——特別是破壞性操作要先確認、搜尋範圍要守邊界那幾條。

產出物的定位見 [README.md](README.md)。這裡只寫「怎麼做」。

## 🔴 查證紀律（最高優先）

**這張圖的全部價值來自「每一條線都實查過」。** 一旦混入憑印象寫的欄位名，整張圖就不能再被信任，因為讀的人無法分辨哪些查過哪些沒有。

- 欄位名、關聯、`on_delete`、必填性、筆數，**一律從 `odoo-dev-19` 查**。不可憑 Odoo 版本印象或其他專案的記憶書寫。
- 18 與 19 之間有實際的破壞性變更（見下方「版本差異」）。**憑 18 的印象寫 19 的欄位，錯誤率很高。**
- 查不到的就標「待確認」，不要給一個看起來合理的名字。寧可留白。
- **觀察與推論分開標示。**外鍵依賴是實查事實；「建議的匯入順序」是從依賴推出來的推論，圖與說明裡都必須標明它是建議。

## 查詢範本

```bash
# 某 model 的必填欄位（store=true 才是真的存在資料庫）
psql -U odoo -d odoo-dev-19 -c "
SELECT f.name, f.ttype, f.relation, f.on_delete
FROM ir_model_fields f JOIN ir_model m ON f.model_id=m.id
WHERE m.model='res.partner' AND f.store IS TRUE AND f.required IS TRUE
ORDER BY f.ttype, f.name;"

# 一群 model 之間的 many2one（ERD 的關係線來源）
psql -U odoo -d odoo-dev-19 -c "
WITH s AS (SELECT unnest(ARRAY['product.template','product.product']) AS m)
SELECT m.model AS src, f.name, f.relation AS tgt, f.required, f.on_delete
FROM ir_model_fields f JOIN ir_model m ON f.model_id=m.id
WHERE m.model IN (SELECT m FROM s) AND f.relation IN (SELECT m FROM s)
  AND f.ttype='many2one' AND f.store IS TRUE
  AND f.name NOT IN ('create_uid','write_uid')
ORDER BY m.model, f.name;"

# many2many 與它的中介表
psql -U odoo -d odoo-dev-19 -c "
SELECT m.model, f.name, f.relation, f.relation_table, f.column1, f.column2
FROM ir_model_fields f JOIN ir_model m ON f.model_id=m.id
WHERE m.model='product.template' AND f.ttype='many2many' AND f.store IS TRUE;"

# 表層約束：CHECK 與 UNIQUE 都不在 ir_model_fields 裡
psql -U odoo -d odoo-dev-19 -c "
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid='res_partner'::regclass;"

# 中介表的實體結構（複合主鍵、NOT NULL、FK 方向）
psql -U odoo -d odoo-dev-19 -c "
SELECT column_name, is_nullable FROM information_schema.columns
WHERE table_name='sale_order_line_invoice_rel' ORDER BY ordinal_position;"

# 欄位標籤與 help 是 jsonb，要取語言鍵
psql -U odoo -d odoo-dev-19 -c "
SELECT f.name, f.field_description->>'en_US' AS label, f.help->>'en_US' AS help
FROM ir_model_fields f JOIN ir_model m ON f.model_id=m.id
WHERE m.model='stock.picking' AND f.name='backorder_id';"
```

## 已經踩過的坑

以下每一條都是實際踩過、驗證過的。不要重踩。

### 資料層

- **`ir_model_fields.compute` 對全部 8469 個 `state='base'` 的欄位都是 NULL。**它只記錄客製欄位的運算式。要判斷原生欄位是不是 compute，只能讀原始碼。
- **`store=true` 不等於使用者可填。**compute + store 的欄位（如 `commercial_partner_id`）在 `ir_model_fields` 裡看起來和一般欄位一模一樣，但匯入時會被重算覆蓋。
- **表層 CHECK 約束不在 `ir_model_fields` 裡。**`res.partner` 的 `name` 是條件式必填（`type='contact'` 時才強制），這條規則只存在 `pg_constraint`，debug mode 的 Fields 清單看不到。
- **`field_description` 與 `help` 是 jsonb。**直接 `SELECT` 會噴 `invalid input syntax for type json`，要用 `->>'en_US'`。
- **`related` 欄位在資料庫裡不存在。**`product.product` 有 15 個欄位（含 `name`、`list_price`）是 related 到 `product_tmpl_id.*`，ORM 會穿透但 SQL 查不到。做報表或跟 RD 談 join 條件時這個差異是關鍵。
- 統計欄位時記得排除 `create_uid` / `write_uid` / `create_date` / `write_date`，它們每個 model 都有，是雜訊。
- **`ir_model` 的 model 數會高估要畫的實體數。**排除 `transient`（wizard）之後還要再排除 SQL view：`purchase.*` 有 6 個非 transient 的 model，但 `purchase.bill.union` 是 view、`purchase.report` 是報表、`purchase.bill.line.match` 是檢視畫面、`purchase.edi.xml.ubl_bis3` 是 EDI 格式，真正有實體表要畫的只有 `purchase.order` 與 `purchase.order.line`。用 `pg_class.relkind` 分辨（`r` 實體表、`v` SQL view）。估算庫存（26 個）與會計（56 個）的工作量前先跑這一步，否則會高估好幾倍。
- **官方 zh_TW 標籤查得到，但不能照單全收。**`odoo-dev-19` 的 zh_TW 是 active 的，`field_description->>'zh_TW'` 全庫 8217/8471 個欄位有值，本圖涵蓋的 128 個 model 欄位中 126 個有翻譯。它是實查事實（使用者切繁中時真的會看到這些字），但品質參差，2026-08-14 逐條比對後確認至少四類問題：
  - **語意錯**：`res.partner.state_id` 譯「狀態」（實為州／省，同庫 `res.city.state_id` 卻譯「州/省」）；`res.partner.bank.partner_id` 譯「科目持有人」（en 為 Account Holder，此處 Account 是帳戶非會計科目）；`res.partner.group_on` 譯「平日」。
  - **中國用字**：「賬」而非「帳」（`autopost_bills` 譯「自動過賬賬單」、`property_account_*_id` 譯「應收／應付賬戶」）。
  - **同概念不同譯**：`customer_rank`「客戶評級」對 `supplier_rank`「供應商排名」；`property_payment_term_id`「客戶支付條款」對 `account.payment.term.name`「付款條件」；`res.company.partner_id`「業務夥伴」對 `res.users.partner_id`「相關的合作夥伴」；`product.template.attribute.line`「產品範本…」對 `.value`「產品模板…」。
  - **缺翻譯**：`res.partner.group_rfq`、`res.partner.bank.l10n_us_bank_account_type` 無 zh_TW。

  引用官方譯法時要標明來源是 zh_TW 語言包；自己改寫成台灣慣用語則屬建議，兩者不可混為一談。圖上 `property_account_receivable_id` 等四條刻意保留專案自訂的台灣會計用語（應收科目／應付科目／客戶付款條件／供應商付款條件），不採官方譯法。136 條屬性行的完整中英對照與疑義清單見 [odoo-v19ce-erd-欄位中英對照表.xlsx](odoo-v19ce-erd-欄位中英對照表.xlsx)（2026-08-18 含採購重建）。**加新模組時記得同步更新它**，否則對照表會與圖不一致。

### Mermaid

- **同一對實體之間畫多條自我參照時，只有最後一條的標籤會被渲染，其餘靜默消失。**解法是合併成一條線、標籤用斜線並列（例如 `parent_id / commercial_partner_id`），並在說明面板列出完整清單。**改完一定要數標籤：唯一標籤數要等於源碼裡的唯一欄位名數。**
- **多對多不要用 `}o--o{` 帶過。**展開成中介表實體，一來符合 ERD 慣例，二來 Odoo 的中介表是真實存在的資料庫表（有複合主鍵、有各自的 `ON DELETE` 方向），那些資訊對規劃有用。
- 實體名不能含點號，用 alias 語法：`res_partner["res.partner"]`。
- 複合主鍵外鍵的標記是 `PK,FK`（逗號），寫成 `PK-FK` 會被當成普通文字。
- `useMaxWidth: false` 時 mermaid 會把實際尺寸寫進 `viewBox` 與 `width`/`height`，那是最可靠的尺寸來源。
- **關係裡引用了沒宣告的實體，mermaid 會自動補一個沒有欄位的空框。**分視圖之後特別容易踩到：`res_company |o--o{ product_template : "company_id"` 這條線把 `res.company` 帶進了商品視圖，畫出一個沒有任何說明的框。解法是明確宣告成邊界節點（只列主鍵，註解寫「邊界 · 完整定義在 X 視圖」），讓它讀起來是刻意的引用而不是漏畫。**改完數節點：實際 `g.node` 數要等於宣告的實體數，多出來的就是被隱含產生的。**

### 瀏覽器與渲染

- **不要移除 SVG 的 `width`/`height` 屬性。**移除後它失去佈局尺寸、`getBoundingClientRect()` 回報 0×0，**整張圖不會被畫出來**。要取尺寸就讀 `viewBox`。
- **不要用 `bbox.width + bbox.x * 2` 推算畫布尺寸。**那假設左右留白相等，並不成立。
- **`requestAnimationFrame` 在背景分頁不觸發。**任何 `await new Promise(r => requestAnimationFrame(r))` 都必須加逾時競速，否則在背景分頁載入時後續程式碼全部卡死，載入指示永遠轉不停。
- **`getBoundingClientRect()` 在 CSS transition 期間回傳的是動畫當下的位置。**做定位計算（例如索引飛行）時，它會與已經更新的 `tx`/`scale` 變數不同步而算錯。改用 SVG 內部座標：`node.getBBox()` 加上 `node.transform.baseVal.consolidate().matrix`。
- **mermaid 靠實際文字寬度決定實體框大小，字型未就緒會量出偏小的框。**渲染前 `await document.fonts.ready`（一樣加逾時）。CDN 版曾經「碰巧正確」，那是靠網路延遲的運氣，不是設計。
- 視窗窄於 860px 時面板是全寬的，「可見區寬度」會變成 0。任何用 `vw() - panelW` 的計算都要處理這種情況。
- **按鈕沒有 `white-space: nowrap` 時，空間不足會把中文逐字斷成直排。**不溢出、不報錯，只是變成一行一個字並撐高整條工具列。`getBoundingClientRect()` 的寬度看不出這件事——**加按鈕後一定要在 390px 實際截圖看**。
- **測深色模式一定要 reload。**只切 `prefers-color-scheme` 而不重新載入時，CSS 變數已經換成新值，但既有元素的 computed color 還是舊的，會量到假的對比度：實測量到 2.27，reload 後其實是 7.87。

## 視圖架構

圖分成四張視圖，不是一張。單張畫滿 24 個實體時全圖適配只剩 2.8px；加上會計、庫存之後會到 50–60 個實體，單張屆時完全不可讀。

| 視圖 id | 內容 | 節點數 | 尺寸 | 適配後字級 |
|---|---|---|---|---|
| `overview` | 模組方塊與接縫，不畫欄位 | 3 | 678×965 | **12.0px** |
| `contacts` | 聯絡人 | 12 | 2734×2493 | 4.6px |
| `product` | 商品主檔 + 2 個邊界節點 | 14 | 4904×1748 | 4.0px |
| `purchase` | 採購 + 7 個邊界節點 | 10 | 2775×1730 | 6.7px |

尺寸為 2026-08-18 加入採購後在 1440×900 重測，適配後字級＝16px 基準字乘上適配縮放。**細節視圖的全圖適配仍然讀不了**，要靠索引跳點（`focusEntity` 有 `READABLE = .75` 的縮放下限，點過去一定看得清）。

**加模組不會撐大既有的細節視圖，但會撐大總覽。**採購加進來後 `overview` 從 2 個方塊 449×698 變成 3 個方塊 678×965，適配字級從 14.6px 掉到 12.0px；`contacts` 與 `product` 的尺寸則完全沒變。總覽是唯一會隨模組數線性成長的視圖，再加三四塊就要考慮改成兩欄排列或分層。

幾條實作約定：

- **總覽也是 erDiagram，不是 flowchart。**這樣三張圖的節點結構一致（都是 `g.node` 加 `entity-{key}-{n}`），`wire()` 一套邏輯通吃。方塊的 key 直接就是視圖 id，點擊時 `switchView(key)`，不必另做對應表。
- **邊界節點**：指向其他視圖的關係，在本視圖宣告一個只有主鍵的同名實體，註解寫「邊界 · 完整定義在 X 視圖」。它不列進 `GROUPS`，所以索引只會有一份。
- **`views[id]` 持有 `el` / `box` / `nodes`。**`box` 不能共用——切過去若沿用前一張的尺寸，`fit()` 會算出錯的縮放；`nodes` 也必須分開，否則 `res_partner` 這種跨視圖出現的 key 會互相覆蓋。
- **`HOME[key]` 決定索引點擊跳去哪張視圖**，由 `GROUPS` 的 `view` 欄位建出來。跨視圖時先 `switchView`，等 `nextFrames()` 之後才飛——隱藏中的節點量不到幾何。
- **先全部量好再隱藏。**boot 的順序是：render 全部 → 逐一量 `box` 並 `wire` → `switchView` 收掉其他張。
- `location.hash` 記住當前視圖，可以寄連結指向特定一張。

## 擴充流程：加一塊模組

1. **查證**。用上面的範本把該群 model 的必填、m2o、m2m、中介表結構、現有筆數全部查出來。先查 model 是否存在（`SELECT model FROM ir_model WHERE model LIKE 'stock.%'`），版本間會有增刪。
2. **決定它進哪張視圖**。掛在既有模組上的少數實體就併進那張；成組的新模組（會計、庫存、採購）自成一張。**自成一張要多做四件事**：`VIEW_IDS` 加 id、工具列 `#viewswitch` 加按鈕、`overview` 的 DSL 加一個模組方塊、`ENTITY` 加那個方塊的 hover 資料。
3. **加 mermaid 實體與關係**到該視圖的 `<pre class="mermaid">`。粒度維持一致：**只列主鍵、外鍵、必填欄位**。指向圖外實體的必填外鍵要列出並在註解標「圖外」；指向其他視圖的，宣告成邊界節點。
4. **加 hover 資料**到 JS 的 `ENTITY` 物件。每個實體都要有，`role` 一句話、`rows` 放實查數字、`flag` 放那個實體最容易踩的坑（危險的用 `warn: true`）。
5. **加索引分組**到 `GROUPS` 陣列，**要帶 `view` 欄位**，key 要與 mermaid 的實體 id 一致。
6. **更新這幾處數字**：工具列副標、`#boot` 的「正在繪製 N 張視圖 · M 個實體」、說明面板「這張圖現在涵蓋什麼」的各段。
7. **加該模組的說明區塊**：結構陷阱、版本差異、以及它的匯入順序（標明是從依賴推出的建議）。
8. **更新對照表** [odoo-v19ce-erd-欄位中英對照表.xlsx](odoo-v19ce-erd-欄位中英對照表.xlsx)：新實體補進「實體對照」、新欄位補進「欄位對照」。中文一律取 `field_description->>'zh_TW'`，**不要自己翻**；查不到就填「（無官方繁中）」。發現誤譯或中國用字寫進「翻譯疑義」分頁，不要在對照欄裡逕行改寫。補完數一次：欄位對照的列數要等於各視圖 mermaid 區塊的屬性行數總和，**邊界節點的主鍵行不計**。
9. **重新組裝**：`python3 build-offline.py`。
10. **驗證**（下一節）。

## 驗證清單

改動後必跑。`file://` 開啟時 viewport 相關的 API 會回報 0，**佈局與定位測不了**，要驗證那些必須起本機伺服器：在本資料夾的 `.claude/launch.json`（preview 工具是從 cwd 找的，不是上一層）暫時加一個 `python3 -m http.server` 設定，測完移除。

逐張視圖檢查，不是只看當前那張：

- [ ] 每張視圖都有渲染，各自的 `viewBox` 寬高 > 0（隱藏中的 `getBoundingClientRect()` 會回 0，改讀 `viewBox`）
- [ ] **各視圖 `g.node` 數 = 該視圖宣告的實體數**（多出來的是關係隱含產生的空框）
- [ ] **各視圖唯一標籤數 = 該視圖源碼裡的唯一欄位名數**（抓自我參照被吃掉的標籤）
- [ ] hover 覆蓋率 = 節點總數，邊界節點也要有卡
- [ ] 索引按鈕數 = 各視圖正典實體數之和（邊界節點不重複計）
- [ ] **跨視圖點索引**：自動切到正確視圖 + 實體落在可見區中心 + 文字 ≥ 10.5px
- [ ] 各視圖初始 `fit()` 的縮放等於手動點「適配」的縮放（抓字型與時序問題）
- [ ] 切換視圖後 `fit()` 正確，沒有沿用前一張的 `box`
- [ ] 總覽方塊點擊會進入對應視圖；`location.hash` 指定的視圖可直接開啟
- [ ] 載入指示會消失、錯誤層沒有顯示
- [ ] 離線版：過濾掉 localhost 後網路請求為 0
- [ ] 390px 實際截圖：工具列沒有溢出、按鈕文字沒有變直排
- [ ] 對比度：小字 ≥ 4.5:1（深淺色都要，**深色要 reload 後才量**）
- [ ] `node ~/.claude/skills/impeccable/scripts/detect.mjs --json index.html`（`em-dash-overuse` 是誤判，它把 CSS 自訂屬性的 `--` 算進去了）

## 版本差異（19 相對於 18，實查發現）

- **`uom.category` 這個 model 在 19 不存在。**計量單位改成 `uom.uom.relative_uom_id` 自我參照 + `relative_factor`，用 `parent_path` 做階層索引。依 18 的 category 設計寫的匯入邏輯在 19 完全不適用。
- **`product.packaging` 被 `product.uom` 取代**（Link between products and their UoMs），必填 `barcode`、`product_id`、`uom_id`，指向變體層。
- `product.combo` / `product.combo.item`、`product.tag` 是 19 有的（是否為新增未查證）。

發現新的版本差異時補在這裡，並註明是實查還是推測。

## 設計約束

視覺沿用既有系統（紙感底色、赭紅 accent、PingFang TC）。以下幾條是 `impeccable` skill 的 craft floor 要求，改動時不要違反：

- **不要 eyebrow**（標題上方的小標籤）。這是硬禁令，標題自己承擔重量。
- 卡片、callout 的彩色左邊框不得超過 1px。要區隔用背景色。
- 字階固定四級，級距 1.125：`--t-xs` / `--t-sm` / `--t-md` / `--t-lg`。**不要新增字級**，需要層次就用 font-weight。
- 只有 400 與 500 兩種字重。
- 動畫 150–260ms，且只用來傳達狀態。
- 章節不編號，除非序列本身帶資訊。
- 說明用漸進揭露（面板 + hover），不要用 modal。
