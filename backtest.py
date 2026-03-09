import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt


def load_weights(weights_csv):
    df = pd.read_csv(weights_csv)
    return df


def backtest_portfolio(weights, assets, start, end):
    # weights: list or array of shape (N,)
    data = yf.download(assets, start=start, end=end, progress=False)["Close"]
    prices = data.fillna(method="ffill").dropna()

    # compute daily returns
    returns = prices.pct_change().dropna()

    port_returns = returns.values @ np.array(weights)

    # cumulative return series
    cum = (1 + port_returns).cumprod() - 1

    stats = {
        "start": start,
        "end": end,
        "cum_return": float(cum[-1]),
        "mean_daily_return": float(port_returns.mean()),
        "std_daily_return": float(port_returns.std()),
    }

    return cum, stats


def run_backtest_for_selected(weights_df, assets, out_dir, windows):
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)

    results = []

    for idx, row in weights_df.iterrows():
        target = row["target_value"]
        weights = row.drop(labels=["target_value"]).values.astype(float)

        for w in windows:
            start, end = w
            cum, stats = backtest_portfolio(weights, assets, start, end)

            stats.update({"target": target, "window_start": start, "window_end": end})
            results.append(stats)

            # save plot
            plt.figure()
            plt.plot(cum)
            plt.title(f"Target={target} {start} to {end}")
            plt.xlabel("Days")
            plt.ylabel("Cumulative Return")
            fname = out_dir / f"bt_target_{target}_from_{start}_to_{end}.png"
            plt.savefig(fname)
            plt.close()

    df = pd.DataFrame(results)
    df.to_csv(out_dir / "backtest_summary.csv", index=False)

    return df


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(description="Backtest saved PSO portfolios")
    parser.add_argument("--weights-csv", required=True)
    parser.add_argument("--assets", nargs='+', required=True)
    parser.add_argument("--out", default="results/backtest")
    parser.add_argument("--windows", nargs='+', help="Windows as start:end (YYYY-MM-DD:YYYY-MM-DD)")

    args = parser.parse_args()

    df_weights = load_weights(args.weights_csv)

    windows = []
    if args.windows:
        for w in args.windows:
            s, e = w.split(":")
            windows.append((s, e))
    else:
        # default quarterly windows from 2024-03-01 to 2025-06-30
        windows = [
            ("2024-03-01", "2024-05-31"),
            ("2024-06-01", "2024-08-31"),
            ("2024-09-01", "2024-11-30"),
            ("2024-12-01", "2025-02-28"),
            ("2025-03-01", "2025-06-30"),
        ]

    df_summary = run_backtest_for_selected(df_weights, args.assets, args.out, windows)
    print("Backtest finished. Summary saved to:", args.out)


if __name__ == "__main__":
    main()
