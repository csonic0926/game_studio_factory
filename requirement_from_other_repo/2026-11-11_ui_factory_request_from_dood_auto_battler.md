# Cross-repo factory request — UI Factory：讓 AI 自己發現 USER 一眼就看出的 UI 問題

## Request metadata

- Status: open
- Date: 2026-11-11
- Source repo: `dood_auto_battler`（Simplest Auto Battler，Godot，CLOSED_BETA mode）
- Request owner: USER（由該 repo 的 Director agent 代為整理）
- Factory target: `ui/`（連帶 review rubric、human decision surface）
- Priority: high

USER 的出發點：

> simplest 系列我想開發出能令 AI 把遊戲做好的、面向 AI 用的工具，當然也包括現在講的 UI
> 我倒是希望你來想

所以這份 request 的目標，不是替某一個遊戲修 UI，而是讓 UI Factory 的流程本身，能在 USER 看到之前抓到這類問題。

---

## 一、發生了甚麼

`take-the-table-ui` 這個 UI design 走完了完整的 v3 流程：

- 草稿 43 至 93，每一版都經兩個獨立審查（completeness + intent）；
- USER 以 exact action 批准草稿 93；
- 全部 production 驗證（verification plan 的每一項「Production adds before acceptance」）都已建成並通過；
- 盲測 chain A / C 及 informed comparison 都做了。

USER 在 TestFlight 玩了 closed beta（build `c7b9411`）後，回報遊戲「真的好玩」，但「UI 問題相當嚴重」。他在幾分鐘內就指出下面九項。這些問題整個 Factory 流程都沒有把它們當作阻擋問題：

| # | USER 原話（節錄） | 背後的原則 |
|---|---|---|
| 1 | 「icon 和 +n% 處理錯了，應該是 same line；如果是攻和血都會加，就應該是兩行，且各顯示一個 %」 | 數值要與它作用的屬性在同一行 |
| 2 | 「黃、藍區域分別是對手和我的桌面，紅圈的 UI 和藍區域左右的兩個 button 都違返這個 meaning」 | 區域代表歸屬；全局操作不放在任何一方的區域 |
| 3 | 「這個 combo 的組成是一種遊玩時的目標…它的注目度不應該是現在這個水平」 | 遊玩目標要顯示進度和下一級回報，注目度要配得上它的重要性 |
| 4 | 「這一堆有明顯的重覆問題（例如：經驗購買 button 和上方的經驗條）」 | 同一資訊只出現一次；相關資訊放在一起 |
| 5 | 「已有一張和已有兩張的 VFX 是任何 auto battler game 都必須做的」 | 類型必備功能不能漏（這項由頭到尾都沒有被設計） |
| 6 | 「繼續 button 我找了好久，一度以為有 bug」 | 主要動作固定位置、最突出 |
| 7 | 「攻防的線很難看清楚（才 4 張⋯ 9 張完全是不能閱讀）」 | 關係類 overlay 有密度上限；改用動畫、分拍表達 |
| 8 | 「商店沒有上鎖（下回合一開始不會重抽）」 | 類型必備功能 |
| 9 | 線的 VFX「顏色不能用現在這個彩度的紅、藍（這個彩色是 card type 的紅、藍、黃、綠在用的）」 | 帶規則意義的顏色不能挪作其他意思 |

Evidence（皆在 `dood_auto_battler` repo）：

- USER 原話：`design/factory/transcript/2026-11-08-closed-beta-c7b9411-verdict.json`
- 該 UI design：`design/ui/take-the-table/`（`UI_DESIGN.md`、四個 JSON artifact）
- 審查紀錄：`design/factory/reviews/take-the-table-ui/v43-*` 至 `v93-*`
- 盲測與比較：`design/studio/runtime_evidence/take-the-table/c7b9411/`
- Idea 查漏：`design/product/idea/inquiries/closed_beta_c7b9411.json`

---

## 二、根本原因（Director 的判斷）

### 1. 審查的力氣花在錯的地方

草稿 52 至 93 大約 40 輪審查，絕大部分 FAIL 都是文字和數字的一致性問題，例如：

- 「1.5 s 要不要加一個 frame 的 slack」
- 「2.6 s 的 slack 要算一個 timer 還是兩個 timer」
- 「attention plan 的 1100 ms 與 verification plan 的 0.5 s + 0.05 s 是否同一個 clock」

這些審查都很嚴謹，但沒有一個審查問過「玩家看得懂這個畫面嗎？」「這個畫面的排位有沒有意義？」。completeness 審查對「每個數字是否一致」有逐條規則，對「版面語義」則沒有任何規則。結果是文字越來越精確，畫面卻沒有變好。

### 2. 沒有可以機械檢查的版面語義規則

上表九項之中，至少六項可以機械檢查：

- 顏色撞了規則色；
- 同一資料在同一畫面出現兩次；
- 主要按鈕不在固定位置，或者對比度不是最高；
- 數字與屬性 icon 不在同一行；
- 某元素放在不屬於它那一方的區域；
- 同一時刻畫面上的線條超過上限。

Factory 現在只有 typography 掃描（字級、溢出、safe area），沒有這類語義檢查。

### 3. 沒有類型必備清單

「已有 1 / 2 張」和「商店上鎖」是 auto battler 的基本功能。Factory 沒有任何地方要求設計者對照類型基本功能清單，所以一個功能如果從未被設計，任何審查都看不到它不存在。

### 4. 給 USER 的決策面太長、太文字

USER 批核時面對的 `UI_DESIGN.md` 決策段落約 150 KB。最後由 Director 另外做了一頁紙摘要，USER 才可以實際作決定。視覺問題用文字描述，USER 很難判斷。這次目標線的選擇，是做了原型、出了 GIF 給 USER 看之後，USER 才能給方向。

### 5. 盲測有抓到，但沒有回流到設計

盲測觀察員其實抓到了多項（icon 讀不懂、「繼續」位置、線條纏亂）。但 UI-H6 等被設計成「記錄、不阻擋」，所以這些發現沒有令設計回頭修正。

---

## 三、請求 UI Factory 提供的能力

### R1. 版面語義規則（可機械檢查）

在 UI design 的 artifact 或 screen contract 中加入可聲明、可檢查的語義：

- **規則色保留**：設計聲明哪些顏色帶規則意義（例如四個 card colour），其他 UI 元素、VFX、線條不得使用。
- **區域歸屬**：每個 surface 聲明區域（例如 rival zone、player zone、global）；每個 placement 聲明它屬於哪一方，放錯區域即 FAIL。
- **主要動作**：每個 surface 聲明唯一的主要動作；它在同一流程的連續畫面中位置固定，並且是視覺上最突出的控件。
- **資訊唯一**：同一個 fact 在同一 surface 只可有一個 persistent placement（現有 information model 已有 fact id，可以直接檢查）。
- **數值對齊**：一個數值與它作用的屬性 icon 必須在同一行；作用於多個屬性，就逐個屬性顯示。
- **overlay 密度**：關係類 overlay（線、箭頭）同一時刻的數量要有上限；超過上限的設計，要改用分拍或動畫。

Factory 提供 checker，並在 production 驗證中跑在 runtime capture 上，不只是在設計文字上。

### R2. 審查 rubric 重排優先次序

- intent 審查第一條必問：「USER 第一眼看這個畫面，會不會看錯或找不到東西？」並要求審查員看 capture 作答，不是讀文字作答。
- completeness 審查對數字和文字一致性設比例原則：不影響玩家、也不影響 verification 結果的文字精度問題，記為 non-blocking。避免設計停在幾十輪的文字修訂。
- 每一輪審查必須包含 R1 的語義檢查結果。

### R3. 類型必備功能清單

- Factory 提供按類型的必備功能清單（auto battler 的起始清單：已有幾張的提示、商店上鎖、刷新、經驗購買、前 N 名視為成功的結果呈現、對手陣容可讀……）。
- UI 及 gameplay design 必須逐項聲明「已有 / 不需要（理由）/ 缺漏」。審查員對照這份清單。

### R4. 給 USER 的決策面

- 每份需要 USER 批核的 design，Factory 都產出一頁摘要（要 USER 拍板的事項、有多個意思的 icon、新舊 capture 並排）作為正式的 human decision view，而非由 Director 另外手寫。
- 視覺選擇以原型 capture／GIF 對比作為標準呈現方式，Factory 提供 frame sequence capture 和並排拼圖的工具。

### R5. USER feedback 回流成規則

- USER 每指出一個 UI 問題，流程要問：「為甚麼 checker 或審查沒有抓到？」並把答案寫成新規則（R1）或新的必問問題（R2）。
- USER 常以實作細節表達方向（例如「z index above all cards」「每張 card 的 VFX start delay x to 1x frames」）。Factory 的 intake 應先把它抽成原則並跟 USER 確認，再落地，而不是逐字照做。

### R6. 盲測發現的回流

- 盲測／comparison 中被標為「記錄、不阻擋」的 UI 讀不懂問題，要在下一份 UI design 中被逐項處理，或由 USER 明確豁免，不能只停留在記錄中。

---

## 四、驗收（這份 request 何時算完成）

1. 以 `dood_auto_battler` 草稿 93 的 artifacts 和 `c7b9411` 的 runtime captures 作 regression case：新的 UI Factory checker 及 rubric，在不參考 USER 原話的情況下，至少抓到上表的 #1、#2、#4、#6、#7、#9。
2. 類型清單能令審查員對 #5 和 #8 報「缺漏」。
3. 一頁 decision view 能由 Factory 直接產出，並包含要 USER 拍板的事項及新舊 capture 對比。
4. 草稿 52–93 那類純文字精度問題，在新的 rubric 下被記為 non-blocking，不再阻擋 REVIEWED。

---

## 五、這個 repo 的後續

`dood_auto_battler` 會在自己的 UI 草稿 94 中先用 project-level 規則實踐 R1–R5（不改 Factory checkout），作為這份 request 的試點。試點結果會補充到本文件。
