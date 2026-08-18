"""Run the daily technical screen across the top-N US stocks by market cap."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from . import indicators as ind
from .config import ScreenerConfig, DEFAULT_CONFIG
from .data import TickerInfo, fetch_price_history, top_n_by_market_cap


@dataclass
class StockSignal:
    ticker: str
    name: str
    market_cap: float
    price: float

    ma_values: Dict[int, Optional[float]] = field(default_factory=dict)

    rsi_value: Optional[float] = None
    rsi_buy_zone: bool = False

    obv_value: Optional[float] = None
    obv_ma_value: Optional[float] = None
    obv_rising: bool = False

    cloud_target: Optional[float] = None
    cloud_distance_pct: Optional[float] = None
    cloud_signal: bool = False

    poc_price: Optional[float] = None
    value_area_low: Optional[float] = None
    value_area_high: Optional[float] = None
    vp_distance_pct: Optional[float] = None
    vp_signal: bool = False

    error: Optional[str] = None

    @property
    def match_count(self) -> int:
        return sum([self.rsi_buy_zone, self.obv_rising, self.cloud_signal, self.vp_signal])

    @property
    def signal_labels(self) -> List[str]:
        labels = []
        if self.rsi_buy_zone:
            labels.append("RSI 30~35")
        if self.obv_rising:
            labels.append("OBV>평균")
        if self.cloud_signal:
            labels.append("구름대 지지")
        if self.vp_signal:
            labels.append("매물대 지지")
        return labels


def evaluate_stock(info: TickerInfo, df: pd.DataFrame, cfg: ScreenerConfig) -> StockSignal:
    close, high, low, volume = df["Close"], df["High"], df["Low"], df["Volume"]
    last_price = float(close.iloc[-1])

    signal = StockSignal(ticker=info.ticker, name=info.name, market_cap=info.market_cap, price=last_price)

    # Moving averages
    for period in cfg.ma_periods:
        ma_series = ind.sma(close, period)
        val = ma_series.iloc[-1]
        signal.ma_values[period] = float(val) if pd.notna(val) else None

    # RSI
    rsi_series = ind.rsi(close, cfg.rsi_period)
    rsi_val = rsi_series.iloc[-1]
    if pd.notna(rsi_val):
        signal.rsi_value = float(rsi_val)
        signal.rsi_buy_zone = cfg.rsi_buy_low <= signal.rsi_value <= cfg.rsi_buy_high

    # OBV vs its own moving average (per-stock baseline)
    obv_series = ind.obv(close, volume)
    obv_ma_series = ind.sma(obv_series, cfg.obv_ma_period)
    obv_val, obv_ma_val = obv_series.iloc[-1], obv_ma_series.iloc[-1]
    if pd.notna(obv_val) and pd.notna(obv_ma_val):
        signal.obv_value = float(obv_val)
        signal.obv_ma_value = float(obv_ma_val)
        signal.obv_rising = signal.obv_value > signal.obv_ma_value

    # Ichimoku cloud: pull back near the bottom of the thickest recent cloud zone
    ich = ind.ichimoku(
        high, low,
        tenkan_period=cfg.tenkan_period,
        kijun_period=cfg.kijun_period,
        senkou_b_period=cfg.senkou_b_period,
        displacement=cfg.displacement,
    )
    target = ind.thickest_cloud_zone(ich, cfg.cloud_lookback, len(close) - 1)
    if target is not None and target > 0:
        signal.cloud_target = target
        dist = (last_price - target) / target
        signal.cloud_distance_pct = dist
        signal.cloud_signal = 0 <= dist <= cfg.cloud_pullback_tolerance

    # Volume profile ("매물대"): price near the Point of Control / value-area low
    vp = ind.volume_profile(
        high, low, close, volume,
        lookback=min(cfg.volume_profile_lookback, len(close)),
        bins=cfg.volume_profile_bins,
        value_area_pct=cfg.value_area_pct,
    )
    if vp is not None:
        signal.poc_price = vp.poc_price
        signal.value_area_low = vp.value_area_low
        signal.value_area_high = vp.value_area_high
        ref = vp.value_area_low if last_price >= vp.value_area_low else vp.poc_price
        dist = abs(last_price - ref) / ref if ref else None
        signal.vp_distance_pct = dist
        signal.vp_signal = dist is not None and dist <= cfg.volume_profile_tolerance

    return signal


def run_screen(cfg: ScreenerConfig = DEFAULT_CONFIG) -> List[StockSignal]:
    print(f"[1/3] 시가총액 상위 {cfg.top_n}개 종목 선정 중...")
    top_infos = top_n_by_market_cap(cfg.top_n)
    if not top_infos:
        raise RuntimeError("시가총액 데이터를 하나도 가져오지 못했습니다. 네트워크 연결을 확인하세요.")
    print(f"  -> {len(top_infos)}개 종목 확정")

    tickers = [i.ticker for i in top_infos]
    print(f"[2/3] {cfg.history_period} 일봉 데이터 다운로드 중...")
    history = fetch_price_history(tickers, period=cfg.history_period)

    print("[3/3] 지표 계산 중...")
    signals: List[StockSignal] = []
    for info in top_infos:
        df = history.get(info.ticker)
        if df is None or df.empty:
            signals.append(StockSignal(info.ticker, info.name, info.market_cap, price=0.0, error="가격 데이터 없음"))
            continue
        min_required = max(cfg.ma_periods) + 5
        if len(df) < min_required:
            signals.append(StockSignal(
                info.ticker, info.name, info.market_cap,
                price=float(df["Close"].iloc[-1]),
                error=f"데이터 부족({len(df)}일 < {min_required}일)",
            ))
            continue
        try:
            signals.append(evaluate_stock(info, df, cfg))
        except Exception as exc:  # noqa: BLE001
            signals.append(StockSignal(info.ticker, info.name, info.market_cap, price=0.0, error=str(exc)))

    signals.sort(key=lambda s: (-s.match_count, s.rsi_value if s.rsi_value is not None else 999))
    return signals
