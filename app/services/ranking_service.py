from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

from app.core.config import RANKING_DIR, AUTO_UPDATE_TOP_LIQUIDITY_COUNT
from app.services.real_kline_service import load_history, list_available_symbols
from app.services.technical_service import build_features
from app.services.formal_backtest_service import multi_strategy_backtest
from app.services.treasure_stock_service import score_treasure
from app.services.financial_import_service import load_financial_history
from app.services.fundamental_service import build_latest_fundamentals, build_quarterly_fundamentals
from app.services.news_service import load_symbol_news
from app.services.stock_universe_service import load_stock_universe, get_stock_meta

RANK_DIR = Path(RANKING_DIR)
RANK_DIR.mkdir(parents=True, exist_ok=True)


def _short_term_score(tech, bt, fundamentals):
    score = 0
    score += 20 if tech.get("last_close", 0) > tech.get("ma20", 0) else 0
    score += 15 if tech.get("ma20", 0) > tech.get("ma60", 0) else 0
    score += min(max(tech.get("pct_20d", 0), 0), 20)
    score += min(tech.get("volume_ratio_20", 0) * 8, 16)
    score += max(min(bt.get("formal_winrate", 0) / 4, 22), 0)
    score += max(min(bt.get("profit_factor", 0) * 4, 16), 0)
    score += max(min((fundamentals.get("roe") or 0)/2, 10), 0)
    score += max(min((fundamentals.get("gross_margin") or 0)/4, 10), 0)
    score += max(min(bt.get("sharpe_like", 0)*4, 10), 0)
    return round(score, 2)


def _strategy(stock, tech, bt):
    close = tech.get("last_close", 0)
    atr_pct = (tech.get("atr_pct", 4) or 4) / 100.0
    pullback = round(max(tech.get("ma20", close), close * (1 - atr_pct*0.6)), 2) if close else 0
    breakout = round(max(close * 1.015, tech.get("recent_high_20", close) * 1.003), 2) if close else 0
    stop = round(min(tech.get("recent_low_20", close), close * (1 - max(0.04, atr_pct*1.2))), 2) if close else 0
    risk = max(close - stop, close * 0.03) if close else 0
    tp1 = round(close + risk * 1.2, 2) if close else 0
    tp2 = round(close + risk * 2.0, 2) if close else 0
    tp3 = round(close + risk * 3.0, 2) if close else 0
    return {
        "pullback_entry": pullback,
        "breakout_entry": breakout,
        "stop_loss": stop,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "holding_days": int(bt.get("best_window", 5)),
        "strategy_comment": f"短線以 {bt.get('best_strategy', 'n/a')} / {bt.get('best_window', 0)} 天窗較佳。"
    }


def _candidate_symbols() -> list[str]:
    saved = list_available_symbols()
    if saved:
        return saved
    uni = load_stock_universe()
    return uni["stock_id"].astype(str).tolist()


def build_rankings():
    universe = _candidate_symbols()
    liquidity_rows = []
    for sid in universe:
        df = load_history(sid, 120)
        if df.empty or len(df) < 120:
            continue
        last_close = pd.to_numeric(df["close"], errors="coerce").iloc[-1]
        avg_amount = (pd.to_numeric(df["close"], errors="coerce") * pd.to_numeric(df["volume"], errors="coerce")).tail(20).mean()
        liquidity_rows.append({"stock_id": sid, "avg_amount": float(avg_amount or 0), "last_close": float(last_close or 0)})
    liquid = sorted(liquidity_rows, key=lambda x: x["avg_amount"], reverse=True)[:AUTO_UPDATE_TOP_LIQUIDITY_COUNT]
    ranked=[]
    treasure=[]
    for row in liquid:
        sid = row["stock_id"]
        stock = get_stock_meta(sid)
        df = load_history(sid, 240)
        tech = build_features(df)
        bt = multi_strategy_backtest(df)
        fund = build_latest_fundamentals(sid)
        quarterly = build_quarterly_fundamentals(sid)
        fin_hist_df = load_financial_history(sid)
        fin_hist = fin_hist_df.to_dict(orient='records') if fin_hist_df is not None and not fin_hist_df.empty else []
        short_score = _short_term_score(tech, bt, fund)
        strategy = _strategy(stock, tech, bt)
        tscore = score_treasure(stock, fund, tech, bt, quarterly, fin_hist)
        news = load_symbol_news(sid)
        item = {
            **stock, **fund, **tech, **bt, **strategy, **tscore,
            "news_count": len(news),
            "latest_news_title": news[0]["title"] if news else "",
            "avg_amount_20": row["avg_amount"],
            "total_score": short_score
        }
        ranked.append(item)
        if tscore.get("is_treasure_candidate"):
            treasure.append(item)
    ranked = sorted(ranked, key=lambda x: (x["total_score"], x.get("avg_amount_20", 0)), reverse=True)
    treasure = sorted(treasure, key=lambda x: (x["treasure_score"], x.get("dcf_margin_of_safety", 0), -x.get("ev_ebitda", 999)), reverse=True)
    for i, item in enumerate(ranked[:10], start=1):
        item["rank"] = i
    for i, item in enumerate(treasure[:10], start=1):
        item["treasure_rank"] = i
    snapshot = {"ranking": ranked[:10], "top5": ranked[:5], "treasure": treasure[:10]}
    (RANK_DIR / "latest_snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot
