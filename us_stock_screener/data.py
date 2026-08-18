"""Market data access via yfinance.

Requires outbound internet access to Yahoo Finance. This will fail in
network-locked-down sandboxes -- run it locally or in an environment
(e.g. a GitHub Actions runner) that can reach finance.yahoo.com.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from .universe import CANDIDATE_TICKERS


@dataclass
class TickerInfo:
    ticker: str
    name: str
    market_cap: float


def fetch_market_caps(tickers: List[str]) -> List[TickerInfo]:
    """Fetch market cap + short name for each candidate ticker.

    Uses `fast_info` where possible (cheap) and falls back to `.info`
    (slower) only when needed. Tickers that fail to fetch are skipped.
    """
    results: List[TickerInfo] = []
    for symbol in tickers:
        try:
            t = yf.Ticker(symbol)
            fast = t.fast_info
            cap = fast.get("market_cap") or fast.get("marketCap")
            name = symbol
            if cap is None:
                info = t.info
                cap = info.get("marketCap")
                name = info.get("shortName", symbol)
            else:
                try:
                    name = t.info.get("shortName", symbol)
                except Exception:
                    name = symbol
            if cap:
                results.append(TickerInfo(symbol, name, float(cap)))
        except Exception as exc:  # noqa: BLE001 - keep the screener resilient
            print(f"  [warn] market cap fetch failed for {symbol}: {exc}")
    return results


def top_n_by_market_cap(n: int, candidates: Optional[List[str]] = None) -> List[TickerInfo]:
    candidates = candidates or CANDIDATE_TICKERS
    infos = fetch_market_caps(candidates)
    infos.sort(key=lambda x: x.market_cap, reverse=True)
    return infos[:n]


def fetch_price_history(tickers: List[str], period: str = "3y") -> Dict[str, pd.DataFrame]:
    """Batch-download daily OHLCV history for all tickers.

    Returns a dict of ticker -> DataFrame with columns
    [Open, High, Low, Close, Volume], sorted by date ascending.
    """
    raw = yf.download(
        tickers,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )

    out: Dict[str, pd.DataFrame] = {}
    if len(tickers) == 1:
        symbol = tickers[0]
        df = raw.dropna(how="all")
        if not df.empty:
            out[symbol] = df
        return out

    for symbol in tickers:
        try:
            df = raw[symbol].dropna(how="all")
        except (KeyError, IndexError):
            continue
        if not df.empty:
            out[symbol] = df
    return out
