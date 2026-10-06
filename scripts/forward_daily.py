"""Daily forward-test job: refresh news+index → prices/labels → resolve → log forecasts.

Pipeline order matters: ``transform_news`` overwrites news.parquet, then
``transform_gdelt`` re-appends GDELT; then LanceDB index is rebuilt.

Example cron (weekdays 18:30 local, from repo root with venv):

    30 18 * * 1-5 cd /path/to/stock-intelligence-agent && \\
      .venv/bin/python scripts/forward_daily.py --tickers AAPL,MSFT,PG >> logs/forward_daily.out 2>&1

Requires GROQ_API_KEY and FINNHUB_API_KEY in .env.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = BASE_DIR / "scripts"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=BASE_DIR, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated forward-test daily job")
    parser.add_argument(
        "--tickers",
        default=None,
        help="Comma-separated tickers for forward_log / GDELT (default: full universe)",
    )
    parser.add_argument(
        "--skip-news",
        action="store_true",
        help="Skip Finnhub + GDELT download/transform and news index rebuild",
    )
    parser.add_argument(
        "--skip-prices",
        action="store_true",
        help="Skip download_prices / transform / build_labels",
    )
    parser.add_argument(
        "--skip-resolve",
        action="store_true",
        help="Skip forward_resolve",
    )
    parser.add_argument(
        "--skip-log",
        action="store_true",
        help="Skip forward_log",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip forward_report (track record summary)",
    )
    parser.add_argument(
        "--gdelt-days",
        type=int,
        default=7,
        help="GDELT timespan in days (default: 7; 1 request/ticker)",
    )
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--date", default=None, help="Override forecast date YYYY-MM-DD")
    args = parser.parse_args()

    py = sys.executable
    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()] if args.tickers else None

    if not args.skip_news:
        # Finnhub raw → parquet (overwrite)
        run([py, str(SCRIPTS / "download_news.py")])
        run([py, str(SCRIPTS / "transform_news.py")])
        # GDELT recent window → merge raw → append parquet
        if tickers:
            for ticker in tickers:
                run(
                    [
                        py,
                        str(SCRIPTS / "download_gdelt.py"),
                        "--ticker",
                        ticker,
                        "--days",
                        str(args.gdelt_days),
                    ]
                )
        else:
            run(
                [
                    py,
                    str(SCRIPTS / "download_gdelt.py"),
                    "--days",
                    str(args.gdelt_days),
                ]
            )
        run([py, str(SCRIPTS / "transform_gdelt.py")])
        run([py, str(SCRIPTS / "build_news_index.py")])

    if not args.skip_prices:
        run([py, str(SCRIPTS / "download_prices.py")])
        run([py, str(SCRIPTS / "transform.py")])
        run([py, str(SCRIPTS / "build_labels.py")])

    if not args.skip_resolve:
        run([py, str(SCRIPTS / "forward_resolve.py")])

    if not args.skip_log:
        log_cmd = [
            py,
            str(SCRIPTS / "forward_log.py"),
            "--k",
            str(args.k),
            "--sleep",
            str(args.sleep),
        ]
        if args.date:
            log_cmd.extend(["--date", args.date])
        if tickers:
            for ticker in tickers:
                run([*log_cmd, "--ticker", ticker])
        else:
            run(log_cmd)

    if not args.skip_report:
        run([py, str(SCRIPTS / "forward_report.py")])

    print("forward_daily done.", flush=True)


if __name__ == "__main__":
    main()
