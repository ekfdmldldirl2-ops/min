"""Tunable thresholds for the screener.

Every value here maps directly to a rule described by the user:
- MA_PERIODS: the moving averages watched on the chart (25/112/224/448 days)
- RSI_LOW / RSI_HIGH: RSI 30~35 is treated as a buy-able zone
- OBV_MA_PERIOD: OBV is compared against its own moving average (per-stock
  baseline, since raw OBV scale differs wildly between tickers)
- ICHIMOKU_*: standard Ichimoku Cloud parameters, plus how far back to look
  for the "thickest" (most overlapping) cloud zone and how close price must
  pull back to that zone's lower edge to count as a buy signal
- VOLUME_PROFILE_*: price-by-volume ("매물대") profile settings used to find
  the Point of Control (heaviest traded price) and the value area around it
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ScreenerConfig:
    # Universe / ranking
    top_n: int = 50
    history_period: str = "3y"

    # Moving averages (days)
    ma_periods: List[int] = field(default_factory=lambda: [25, 112, 224, 448])

    # RSI
    rsi_period: int = 14
    rsi_buy_low: float = 30.0
    rsi_buy_high: float = 35.0

    # OBV
    obv_ma_period: int = 20

    # Ichimoku cloud ("구름대")
    tenkan_period: int = 9
    kijun_period: int = 26
    senkou_b_period: int = 52
    displacement: int = 26
    cloud_lookback: int = 120          # bars searched for the thickest cloud zone
    cloud_pullback_tolerance: float = 0.02   # price within 2% above the zone's bottom

    # Volume profile ("매물대")
    volume_profile_lookback: int = 252  # ~1 trading year
    volume_profile_bins: int = 40
    value_area_pct: float = 0.70
    volume_profile_tolerance: float = 0.02   # price within 2% of POC / value-area low

    # Ranking of results
    min_signals_to_highlight: int = 2   # how many of the 4 conditions to flag as "관심 종목"


DEFAULT_CONFIG = ScreenerConfig()
