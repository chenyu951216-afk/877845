from __future__ import annotations
from pathlib import Path
import json
from typing import Optional
import pandas as pd
import requests

from app.core.config import PRICE_HISTORY_DIR, YFINANCE_ENABLED, YFINANCE_START
from app.services.stock_universe_service import get_stock_meta

PRICE_DIR = Path(PRICE_HISTORY_DIR)
PRICE_DIR.mkdir(parents=True, exist_ok=True)
META_DIR = PRICE_DIR / "_meta"
META_DIR.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session()


def _clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    cols = {c.lower(): c for c in df.columns}
    rename = {}
    for key in ["date", "open", "high", "low", "close", "volume"]:
        for c in df.columns:
            if c.lower() == key:
                rename[c] = key
                break
    df = df.rename(columns=rename)
    if "date" not in df.columns:
        df = df.reset_index().rename(columns={df.index.name or "index": "date"})
    out = df[[c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]].copy()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    for c in ["open", "high", "low", "close", "volume"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["date", "open", "high", "low", "close"]).drop_duplicates(subset=["date"]).sort_values("date")
    out["volume"] = out["volume"].fillna(0)
    return out


def fetch_history_yfinance(stock_id: str, start: str = YFINANCE_START) -> pd.DataFrame:
    meta = get_stock_meta(stock_id)
    ticker = meta.get("yf_symbol") or f"{stock_id}.TW"
    if not YFINANCE_ENABLED:
        return pd.DataFrame()
    import yfinance as yf
    df = yf.download(ticker, start=start, auto_adjust=False, progress=False)
    if df is None or df.empty and ticker.endswith(".TW"):
        ticker = f"{stock_id}.TWO"
        df = yf.download(ticker, start=start, auto_adjust=False, progress=False)
    return _clean_ohlcv(df)


def save_history(stock_id: str, df: pd.DataFrame, source: str = "yfinance") -> str:
    path = PRICE_DIR / f"{stock_id}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    (META_DIR / f"{stock_id}.json").write_text(json.dumps({"source": source, "rows": len(df)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def update_symbol_history(stock_id: str, start: Optional[str] = None) -> dict:
    df = fetch_history_yfinance(stock_id, start=start or YFINANCE_START)
    if df.empty:
        raise ValueError(f"抓不到 {stock_id} 歷史K線")
    path = save_history(stock_id, df, source="yfinance")
    latest = df.iloc[-1].to_dict()
    return {"stock_id": stock_id, "rows": len(df), "saved_to": path, "latest_date": latest.get("date"), "latest_close": float(latest.get("close", 0))}


def load_saved_history(stock_id: str) -> pd.DataFrame:
    path = PRICE_DIR / f"{stock_id}.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
