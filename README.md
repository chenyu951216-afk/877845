# TW Stock Bot v15 實戰自動更新版

這版已從「CSV / sample 為主」改成「真實資料自動抓取、本地落地、每日更新、再做排名 / 財報 / 回測」。

## 這版重點
- 全台股股票清單自動抓取（TWSE / TPEX）
- 台股歷史日K自動抓取並存檔（預設 yfinance，台股 `.TW` / `.TWO`）
- MOPS HTML parsing：自動抓季報 / 年報欄位並整理成標準 CSV
- 每日自動抓新聞（Google News RSS）
- 自動重建短線排名 / 寶藏股 / thesis snapshot
- 保留手動匯入與批次匯入機制
- 回測升級：多策略、多持有窗、ATR 風控、成本 / 稅 / 滑價
- 所有資料都落地到 `data/`，方便後續擴充 AI、排程、資料庫化

## 安裝
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 建議 `.env`
```env
USE_SAMPLE_DATA=false
AUTO_UPDATE_ON_STARTUP=true
AUTO_UPDATE_DAILY=true
AUTO_UPDATE_HOUR=19
AUTO_UPDATE_MINUTE=30
AUTO_UPDATE_FETCH_FINANCIALS=true
AUTO_UPDATE_FETCH_NEWS=true
AUTO_UPDATE_TOP_LIQUIDITY_COUNT=300
YFINANCE_ENABLED=true
MOPS_ENABLED=true
NEWS_ENABLED=true
```

## 自動資料流
1. 啟動時抓全台股清單
2. 抓各股票歷史日K並存到 `data/history/`
3. 抓 MOPS 季 / 年財報並存到 `data/fundamentals/`
4. 抓個股新聞到 `data/news/`
5. 重算排行榜並輸出 `data/ranking/latest_snapshot.json`
6. 背景執行每日定時更新

## 主要資料夾
- `data/history/`：日K歷史資料
- `data/fundamentals/annual/`：年財報整理後 CSV
- `data/fundamentals/quarterly/`：季財報整理後 CSV
- `data/fundamentals/latest/`：最近四季摘要 JSON
- `data/news/`：個股新聞 JSON
- `data/ranking/latest_snapshot.json`：最新排名快照
- `data/update_status.json`：最近一次日更狀態

## 頁面
- `/` Dashboard
- `/ranking` 短線排行榜
- `/treasure` 長線寶藏股
- `/backtest` 回測摘要
- `/import-tool` 手動匯入 + 一鍵抓真資料

## 目前功能
### 1. 真實台股資料自動抓取
- 自動建立全台股 universe
- 自動抓歷史 K 線
- 自動儲存 CSV
- 未找到本地資料時會先嘗試線上抓取

### 2. 真實財報
- MOPS HTML parsing
- 季度與年度欄位標準化
- 自動輸出 revenue / gross_margin / roe / eps / operating_cf / capex / free_cf
- 可做 treasure / thesis / DCF / EV/EBITDA

### 3. 新聞
- 每日抓個股相關新聞 RSS
- 排名內可附帶最新新聞標題數量

### 4. 排名
- 短線排名：趨勢、量能、報酬、回測、流動性
- 寶藏股排名：估值、財務品質、現金流、配息、DCF、EV/EBITDA

### 5. 回測
- 多策略：breakout / pullback / trend_follow / mean_revert
- 多持有週期：3 / 5 / 10 / 15 天
- 成本 / 證交稅 / 滑價納入
- ATR 式止損 / 獲利出場雛形

## 你要求的「全歷史K線（需要額外資料源）」
這版已先接入 `yfinance` 做完整日K歷史來源，對多數台股夠用。
若你之後要更完整的：
- 分鐘K / Tick
- 還原權息精準版
- 更長更穩定的法人 / 籌碼 / 分點 / 月營收 / 財測
建議下一版再接專業資料源或自己的資料庫。

## 已知限制
- MOPS HTML 頁面格式偶爾會改，解析器已做容錯但仍可能需微調
- 新聞目前是 RSS 級別，不是付費新聞全文 API
- 回測目前是日K級研究版，不是撮合引擎級別
- 若你要「真的非常完整」的全市場長年歷史與分鐘回測，建議下一步接 PostgreSQL + 專業行情源
