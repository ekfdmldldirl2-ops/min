"""Technical indicator calculations.

All functions take/return pandas Series or DataFrames indexed by date and
avoid look-ahead bias (Ichimoku's leading spans are shifted forward exactly
the way a charting platform would draw them).
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Moving averages
# ---------------------------------------------------------------------------

def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


# ---------------------------------------------------------------------------
# RSI (Wilder's smoothing, the standard used by most charting platforms)
# ---------------------------------------------------------------------------

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    out = out.where(avg_loss != 0.0, 100.0)  # no losses at all -> RSI 100
    return out


# ---------------------------------------------------------------------------
# On-Balance Volume
# ---------------------------------------------------------------------------

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume).cumsum()


# ---------------------------------------------------------------------------
# Ichimoku cloud
# ---------------------------------------------------------------------------

@dataclass
class IchimokuResult:
    tenkan: pd.Series
    kijun: pd.Series
    senkou_a: pd.Series
    senkou_b: pd.Series
    cloud_top: pd.Series
    cloud_bottom: pd.Series
    cloud_thickness: pd.Series


def ichimoku(
    high: pd.Series,
    low: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
    displacement: int = 26,
) -> IchimokuResult:
    def midline(period: int) -> pd.Series:
        return (high.rolling(period).max() + low.rolling(period).min()) / 2.0

    tenkan = midline(tenkan_period)
    kijun = midline(kijun_period)
    senkou_a = ((tenkan + kijun) / 2.0).shift(displacement)
    senkou_b = midline(senkou_b_period).shift(displacement)

    cloud_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    cloud_bottom = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)
    thickness = cloud_top - cloud_bottom

    return IchimokuResult(tenkan, kijun, senkou_a, senkou_b, cloud_top, cloud_bottom, thickness)


def thickest_cloud_zone(ich: IchimokuResult, lookback: int, as_of_index: int) -> Optional[float]:
    """Find the bottom price of the thickest (most overlapping) cloud zone
    within the last `lookback` bars up to `as_of_index`. That thick zone
    represents where the most Senkou-span history has piled up -- treated
    here as the strongest support band, matching how the user reads a dense
    cloud region as a buy zone at its lower edge.
    """
    start = max(0, as_of_index - lookback + 1)
    window_thickness = ich.cloud_thickness.iloc[start : as_of_index + 1]
    window_bottom = ich.cloud_bottom.iloc[start : as_of_index + 1]

    valid = window_thickness.dropna()
    if valid.empty:
        return None

    idx = valid.idxmax()
    bottom = window_bottom.loc[idx]
    return float(bottom) if pd.notna(bottom) else None


# ---------------------------------------------------------------------------
# Volume profile ("매물대") -- Point of Control + value area
# ---------------------------------------------------------------------------

@dataclass
class VolumeProfileResult:
    poc_price: float          # price level with the heaviest traded volume
    value_area_low: float
    value_area_high: float
    bin_edges: np.ndarray
    bin_volume: np.ndarray


def volume_profile(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    lookback: int,
    bins: int,
    value_area_pct: float = 0.70,
) -> Optional[VolumeProfileResult]:
    h = high.iloc[-lookback:]
    l = low.iloc[-lookback:]
    c = close.iloc[-lookback:]
    v = volume.iloc[-lookback:]

    valid = h.notna() & l.notna() & v.notna()
    h, l, c, v = h[valid], l[valid], c[valid], v[valid]
    if h.empty:
        return None

    price_min = float(l.min())
    price_max = float(h.max())
    if price_max <= price_min:
        return None

    edges = np.linspace(price_min, price_max, bins + 1)
    bin_volume = np.zeros(bins)

    # Distribute each day's volume across the bins its high/low range
    # overlaps, weighted by the fraction of the day's range in each bin.
    # This approximates a real volume-at-price profile far better than
    # simply bucketing by the closing price alone.
    for day_low, day_high, day_vol in zip(l.to_numpy(), h.to_numpy(), v.to_numpy()):
        if day_vol <= 0:
            continue
        if day_high <= day_low:
            bin_idx = np.clip(np.searchsorted(edges, day_low, side="right") - 1, 0, bins - 1)
            bin_volume[bin_idx] += day_vol
            continue

        lo_idx = np.clip(np.searchsorted(edges, day_low, side="right") - 1, 0, bins - 1)
        hi_idx = np.clip(np.searchsorted(edges, day_high, side="right") - 1, 0, bins - 1)
        span = hi_idx - lo_idx + 1
        bin_volume[lo_idx : hi_idx + 1] += day_vol / span

    poc_idx = int(np.argmax(bin_volume))
    poc_price = float((edges[poc_idx] + edges[poc_idx + 1]) / 2.0)

    total_volume = bin_volume.sum()
    target = total_volume * value_area_pct
    included = {poc_idx}
    acc = bin_volume[poc_idx]
    lo, hi = poc_idx, poc_idx
    while acc < target and (lo > 0 or hi < bins - 1):
        left_vol = bin_volume[lo - 1] if lo > 0 else -1
        right_vol = bin_volume[hi + 1] if hi < bins - 1 else -1
        if right_vol >= left_vol:
            hi += 1
            acc += bin_volume[hi]
            included.add(hi)
        else:
            lo -= 1
            acc += bin_volume[lo]
            included.add(lo)

    value_area_low = float(edges[lo])
    value_area_high = float(edges[hi + 1])

    return VolumeProfileResult(poc_price, value_area_low, value_area_high, edges, bin_volume)
