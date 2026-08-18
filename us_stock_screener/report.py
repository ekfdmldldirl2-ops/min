"""Format screening results as console text, Markdown, and CSV."""

import csv
import io
from datetime import date
from typing import List

from .config import ScreenerConfig
from .screener import StockSignal


def _fmt(x, digits=2):
    return "N/A" if x is None else f"{x:,.{digits}f}"


def _fmt_pct(x, digits=1):
    return "N/A" if x is None else f"{x * 100:+.{digits}f}%"


def to_markdown(signals: List[StockSignal], cfg: ScreenerConfig, as_of: date = None) -> str:
    as_of = as_of or date.today()
    lines = [
        f"# 미국 대형주 기술적 스크리닝 ({as_of.isoformat()})",
        "",
        f"- 대상: 시가총액 상위 {cfg.top_n}개",
        f"- 조건: RSI {cfg.rsi_buy_low:.0f}~{cfg.rsi_buy_high:.0f} / "
        f"OBV > {cfg.obv_ma_period}일 평균 / 구름대 최다밀집구간 하단 {cfg.cloud_pullback_tolerance*100:.0f}% 이내 / "
        f"매물대(POC·Value Area 하단) {cfg.volume_profile_tolerance*100:.0f}% 이내",
        "",
    ]

    highlighted = [s for s in signals if s.error is None and s.match_count >= cfg.min_signals_to_highlight]
    if highlighted:
        lines.append(f"## 관심 종목 (조건 {cfg.min_signals_to_highlight}개 이상 충족)")
        lines.append("")
        for s in highlighted:
            lines.append(f"- **{s.ticker}** ({s.name}): {', '.join(s.signal_labels)} — 현재가 {_fmt(s.price)}")
        lines.append("")
    else:
        lines.append(f"## 관심 종목: 없음 (조건 {cfg.min_signals_to_highlight}개 이상 충족한 종목 없음)")
        lines.append("")

    ma_cols = "".join(f" MA{p} |" for p in cfg.ma_periods)
    header = f"| # | 티커 | 종목명 | 현재가 |{ma_cols} RSI | OBV>평균 | 구름대 목표가(이격) | 매물대 POC(이격) | 매칭 |"
    sep = "|---" * (5 + len(cfg.ma_periods) + 4) + "|"
    lines.append(header)
    lines.append(sep)

    for i, s in enumerate(signals, start=1):
        if s.error:
            lines.append(f"| {i} | {s.ticker} | {s.name} | 오류: {s.error} |" + " - |" * (len(cfg.ma_periods) + 4))
            continue
        ma_vals = "".join(f" {_fmt(s.ma_values.get(p))} |" for p in cfg.ma_periods)
        obv_flag = "✅" if s.obv_rising else "—"
        cloud = f"{_fmt(s.cloud_target)} ({_fmt_pct(s.cloud_distance_pct)})" if s.cloud_target else "N/A"
        vp = f"{_fmt(s.poc_price)} ({_fmt_pct(s.vp_distance_pct)})" if s.poc_price else "N/A"
        lines.append(
            f"| {i} | {s.ticker} | {s.name} | {_fmt(s.price)} |{ma_vals} "
            f"{_fmt(s.rsi_value, 1)} | {obv_flag} | {cloud} | {vp} | {s.match_count}/4 |"
        )

    return "\n".join(lines) + "\n"


def to_csv(signals: List[StockSignal], cfg: ScreenerConfig) -> str:
    buf = io.StringIO()
    fieldnames = (
        ["ticker", "name", "market_cap", "price"]
        + [f"ma{p}" for p in cfg.ma_periods]
        + ["rsi", "rsi_buy_zone", "obv_rising", "cloud_target", "cloud_distance_pct", "cloud_signal",
           "poc_price", "value_area_low", "value_area_high", "vp_distance_pct", "vp_signal",
           "match_count", "error"]
    )
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for s in signals:
        row = {
            "ticker": s.ticker, "name": s.name, "market_cap": s.market_cap, "price": s.price,
            "rsi": s.rsi_value, "rsi_buy_zone": s.rsi_buy_zone, "obv_rising": s.obv_rising,
            "cloud_target": s.cloud_target, "cloud_distance_pct": s.cloud_distance_pct,
            "cloud_signal": s.cloud_signal, "poc_price": s.poc_price,
            "value_area_low": s.value_area_low, "value_area_high": s.value_area_high,
            "vp_distance_pct": s.vp_distance_pct, "vp_signal": s.vp_signal,
            "match_count": s.match_count, "error": s.error,
        }
        for p in cfg.ma_periods:
            row[f"ma{p}"] = s.ma_values.get(p)
        writer.writerow(row)
    return buf.getvalue()


def print_console(signals: List[StockSignal], cfg: ScreenerConfig) -> None:
    print(to_markdown(signals, cfg))
