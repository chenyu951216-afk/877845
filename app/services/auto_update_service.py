from __future__ import annotations
from pathlib import Path
import json
import threading
import time
from datetime import datetime, timedelta

from app.core.config import (
    AUTO_UPDATE_DAILY, AUTO_UPDATE_FETCH_FINANCIALS, AUTO_UPDATE_FETCH_NEWS,
    AUTO_UPDATE_HOUR, AUTO_UPDATE_MINUTE, YFINANCE_START, APP_DATA_DIR,
)
from app.services.stock_universe_service import fetch_stock_universe, load_stock_universe
from app.services.market_data_service import update_symbol_history
from app.services.mops_financial_service import fetch_financial_history_from_mops
from app.services.news_service import fetch_symbol_news
from app.services.ranking_service import build_rankings

STATUS_PATH = Path(APP_DATA_DIR) / "update_status.json"
_LOCK = threading.Lock()
_STARTED = False


def _write_status(payload: dict):
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_full_refresh(limit: int | None = None) -> dict:
    with _LOCK:
        fetch_stock_universe(force=False)
        uni = load_stock_universe()
        rows = uni.to_dict(orient="records")
        if limit:
            rows = rows[:limit]
        results = {"updated_prices": 0, "updated_financials": 0, "updated_news": 0, "errors": []}
        for row in rows:
            sid = str(row["stock_id"])
            try:
                update_symbol_history(sid, start=YFINANCE_START)
                results["updated_prices"] += 1
            except Exception as e:
                results["errors"].append({"stock_id": sid, "stage": "price", "error": str(e)})
            if AUTO_UPDATE_FETCH_FINANCIALS:
                try:
                    fetch_financial_history_from_mops(sid)
                    results["updated_financials"] += 1
                except Exception as e:
                    results["errors"].append({"stock_id": sid, "stage": "financial", "error": str(e)})
            if AUTO_UPDATE_FETCH_NEWS:
                try:
                    fetch_symbol_news(sid)
                    results["updated_news"] += 1
                except Exception as e:
                    results["errors"].append({"stock_id": sid, "stage": "news", "error": str(e)})
        ranking = build_rankings()
        results["ranking_top5"] = [f"{x['stock_id']} {x['name']}" for x in ranking.get("top5", [])]
        results["finished_at"] = datetime.now().isoformat()
        _write_status(results)
        return results


def load_update_status() -> dict:
    if STATUS_PATH.exists():
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    return {}


def _seconds_until_target(hour: int, minute: int) -> float:
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _daily_loop():
    while True:
        time.sleep(max(_seconds_until_target(AUTO_UPDATE_HOUR, AUTO_UPDATE_MINUTE), 30))
        try:
            run_full_refresh()
        except Exception as e:
            _write_status({"error": str(e), "failed_at": datetime.now().isoformat()})


def start_scheduler_if_needed():
    global _STARTED
    if _STARTED or not AUTO_UPDATE_DAILY:
        return
    t = threading.Thread(target=_daily_loop, daemon=True)
    t.start()
    _STARTED = True
