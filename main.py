#!/usr/bin/env python3
"""CLI entry point for the daily US large-cap technical screener.

Usage:
    python3 main.py                       # run with defaults, print + save results/latest.md
    python3 main.py --top-n 30            # screen top 30 instead of top 50
    python3 main.py --rsi-low 25 --rsi-high 35
    python3 main.py --out-dir results     # where to write latest.md / latest.csv
"""

import argparse
import dataclasses
import sys
from datetime import date, timezone
from pathlib import Path

from us_stock_screener.config import ScreenerConfig
from us_stock_screener.report import print_console, to_csv, to_markdown
from us_stock_screener.screener import run_screen


def parse_args() -> ScreenerConfig:
    cfg = ScreenerConfig()
    p = argparse.ArgumentParser(description="US large-cap technical screener")
    p.add_argument("--top-n", type=int, default=cfg.top_n)
    p.add_argument("--rsi-low", type=float, default=cfg.rsi_buy_low)
    p.add_argument("--rsi-high", type=float, default=cfg.rsi_buy_high)
    p.add_argument("--obv-ma-period", type=int, default=cfg.obv_ma_period)
    p.add_argument("--cloud-tolerance", type=float, default=cfg.cloud_pullback_tolerance,
                   help="fraction, e.g. 0.02 = 2%%")
    p.add_argument("--vp-tolerance", type=float, default=cfg.volume_profile_tolerance,
                   help="fraction, e.g. 0.02 = 2%%")
    p.add_argument("--min-signals", type=int, default=cfg.min_signals_to_highlight)
    p.add_argument("--out-dir", type=str, default="results")
    p.add_argument("--no-save", action="store_true", help="print only, don't write files")
    args = p.parse_args()

    cfg = dataclasses.replace(
        cfg,
        top_n=args.top_n,
        rsi_buy_low=args.rsi_low,
        rsi_buy_high=args.rsi_high,
        obv_ma_period=args.obv_ma_period,
        cloud_pullback_tolerance=args.cloud_tolerance,
        volume_profile_tolerance=args.vp_tolerance,
        min_signals_to_highlight=args.min_signals,
    )
    cfg._out_dir = args.out_dir  # type: ignore[attr-defined]
    cfg._no_save = args.no_save  # type: ignore[attr-defined]
    return cfg


def main() -> int:
    cfg = parse_args()
    try:
        signals = run_screen(cfg)
    except Exception as exc:  # noqa: BLE001
        print(f"[오류] 스크리닝 실패: {exc}", file=sys.stderr)
        return 1

    print_console(signals, cfg)

    if not getattr(cfg, "_no_save", False):
        out_dir = Path(getattr(cfg, "_out_dir", "results"))
        out_dir.mkdir(parents=True, exist_ok=True)
        today = date.today()

        md = to_markdown(signals, cfg, as_of=today)
        (out_dir / "latest.md").write_text(md, encoding="utf-8")
        (out_dir / f"{today.isoformat()}.md").write_text(md, encoding="utf-8")

        csv_text = to_csv(signals, cfg)
        (out_dir / "latest.csv").write_text(csv_text, encoding="utf-8")

        print(f"\n결과 저장 완료: {out_dir}/latest.md, {out_dir}/latest.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
