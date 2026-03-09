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
    prices = data.ffill().dropna()

    # compute daily log-returns
    returns = np.log(prices / prices.shift(1)).dropna()

    # portfolio daily log-returns (T,)
    port_returns = returns.values @ np.array(weights)

    # cumulative simple return series from log-returns
    cum_values = np.exp(np.cumsum(port_returns)) - 1
    cum = pd.Series(cum_values, index=returns.index)

    stats = {
        "start": start,
        "end": end,
        "cum_return": float(cum.iloc[-1]) if len(cum) > 0 else 0.0,
        "mean_daily_return": float(port_returns.mean()) if len(port_returns) > 0 else 0.0,  # mean log-return
        "std_daily_return": float(port_returns.std()) if len(port_returns) > 0 else 0.0,  # std of log-returns
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


def plot_comparison_for_indices(weights_df, assets, out_dir, windows, indices):
    out_dir = Path(out_dir) / "comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)

    for start, end in windows:
        plt.figure()
        for idx in indices:
            if idx < 0 or idx >= len(weights_df):
                continue

            row = weights_df.iloc[idx]
            target = float(row["target_value"]) if "target_value" in row.index else float(row.iloc[0])
            weights = row.drop(labels=["target_value"]).values.astype(float)

            data = yf.download(assets, start=start, end=end, progress=False)["Close"]
            prices = data.ffill().dropna()

            # use log-returns consistent with training
            returns = np.log(prices / prices.shift(1)).dropna()
            port_returns = returns.values @ np.array(weights)
            cum_values = np.exp(np.cumsum(port_returns)) - 1
            cum = pd.Series(cum_values, index=returns.index)

            # annualize target (assume daily log-return)
            try:
                annual_target = np.exp(float(target) * 252) - 1
            except Exception:
                annual_target = float(target) * 252

            # compute final cumulative return to show actual performance
            final_ret = float(cum.iloc[-1]) if len(cum) > 0 else 0.0
            label = f"idx={idx} final={final_ret*100:.2f}% target_ann={annual_target*100:.1f}%"
            plt.plot(cum.index, cum.values, label=label)

        plt.title(f"Comparison of selected portfolios {start} to {end}")
        plt.xlabel("Days")
        plt.ylabel("Cumulative Return")
        plt.legend()
        fname = out_dir / f"comparison_{start}_to_{end}.png"
        plt.savefig(fname, bbox_inches="tight")
        plt.close()


def aggregate_comparison(weights_df, assets, out_dir, indices):
    out_dir = Path(out_dir) / "comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)

    # overall period from earliest window available in backtest defaults
    # If weights_df came from weights CSV only, use a sensible default range
    overall_start = "2024-03-01"
    overall_end = "2025-06-30"

    plt.figure()

    data = yf.download(assets, start=overall_start, end=overall_end, progress=False)["Close"]
    prices = data.ffill().dropna()
    # use log-returns
    returns = np.log(prices / prices.shift(1)).dropna()
    for idx in indices:
        if idx < 0 or idx >= len(weights_df):
            continue

        row = weights_df.iloc[idx]
        target = float(row["target_value"]) if "target_value" in row.index else float(row.iloc[0])
        weights = row.drop(labels=["target_value"]).values.astype(float)

        port_returns = returns.values @ np.array(weights)
        cum_values = np.exp(np.cumsum(port_returns)) - 1
        cum = pd.Series(cum_values, index=returns.index)

        try:
            annual_target = np.exp(float(target) * 252) - 1
        except Exception:
            annual_target = float(target) * 252

        label = f"idx={idx} target={annual_target*100:.2f}%"
        plt.plot(cum.index, cum.values, label=label)

    plt.title(f"Aggregate comparison {overall_start} to {overall_end}")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.legend()
    fname = out_dir / f"aggregate_comparison_{overall_start}_to_{overall_end}.png"
    plt.savefig(fname, bbox_inches="tight")
    plt.close()


def plot_asset_contributions(weights_df, assets, out_dir, indices, start="2024-03-01", end="2025-06-30"):
    out_dir = Path(out_dir) / "contributions"
    out_dir.mkdir(parents=True, exist_ok=True)

    data = yf.download(assets, start=start, end=end, progress=False)["Close"]
    prices = data.ffill().dropna()

    # price relative to first available day
    price_rel = prices / prices.iloc[0]

    summaries = []

    for idx in indices:
        if idx < 0 or idx >= len(weights_df):
            continue

        row = weights_df.iloc[idx]
        weights = row.drop(labels=["target_value"]).values.astype(float)

        # asset value series (starting capital = 1)
        asset_values = price_rel * weights
        portfolio_value = asset_values.sum(axis=1)

        # save stacked area plot of contributions
        plt.figure(figsize=(10, 5))
        plt.stackplot(prices.index, *(asset_values[col] for col in asset_values.columns), labels=asset_values.columns)
        plt.plot(prices.index, portfolio_value, color="k", linewidth=1.5, label="Portfolio total")
        plt.title(f"Asset contributions idx={idx} (start {start} to {end})")
        plt.xlabel("Date")
        plt.ylabel("Value (start=1)")
        plt.legend(loc="upper left")
        fname = out_dir / f"contrib_idx_{idx}_{start}_to_{end}.png"
        plt.savefig(fname, bbox_inches="tight")
        plt.close()

        # summary stats (use log-returns for consistency)
        total_return = float(portfolio_value.iloc[-1] - 1)
        num_days = len(portfolio_value.index)
        ann_return = (1 + total_return) ** (252 / num_days) - 1 if num_days > 0 else 0.0
        daily_rets = np.log(portfolio_value / portfolio_value.shift(1)).dropna()
        ann_vol = float(daily_rets.std() * (252 ** 0.5)) if len(daily_rets) > 0 else 0.0

        final_asset_vals = asset_values.iloc[-1]
        contrib_pct = (final_asset_vals / final_asset_vals.sum()).to_dict()

        summaries.append({
            "idx": idx,
            "total_return": total_return,
            "annual_return": ann_return,
            "annual_vol": ann_vol,
            **{f"w_{i}": float(weights[i]) for i in range(len(weights))},
            **{f"contrib_w{i}": float(contrib_pct[c]) for i, c in enumerate(asset_values.columns)},
        })

    df_sum = pd.DataFrame(summaries)
    csv_path = Path(out_dir) / "contributions_summary.csv"
    df_sum.to_csv(csv_path, index=False)

    return df_sum, csv_path


def monthly_snapshots(weights_df, assets, out_dir, indices, start="2024-01-01", end="2025-06-30", freq="ME"):
    """
    Compute cumulative return snapshots for selected portfolios at monthly (or quarterly) frequency.
    Saves CSV `selected_portfolios_monthly.csv` and a comparative plot.
    """
    out_dir = Path(out_dir) / "comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Download full price series
    data = yf.download(assets, start=start, end=end, progress=False)["Close"]
    prices = data.ffill().dropna()
    # use log-returns for portfolio construction
    returns = np.log(prices / prices.shift(1)).dropna()

    # Build snapshots (month ends)
    rng = pd.date_range(start=start, end=end, freq=freq)

    # Prepare results table: rows dates, columns per portfolio idx
    cols = [f"idx_{i}" for i in indices]
    df_res = pd.DataFrame(index=rng, columns=cols, dtype=float)

    # Also collect labels for legend (annualized target)
    labels = {}

    for pos, idx in enumerate(indices):
        if idx < 0 or idx >= len(weights_df):
            continue
        row = weights_df.iloc[idx]
        target = float(row["target_value"]) if "target_value" in row.index else float(row.iloc[0])
        weights = row.drop(labels=["target_value"]).values.astype(float)

        # portfolio daily log-returns and cumulative simple returns
        port_returns = returns.values @ np.array(weights)
        cum_values = np.exp(np.cumsum(port_returns)) - 1
        cum = pd.Series(cum_values, index=returns.index)
        cum_index = cum.index

        for date in rng:
            # find first available date >= snapshot date
            sel = cum_index.searchsorted(date)
            if sel >= len(cum):
                # use last available
                val = float(cum.iloc[-1]) if len(cum) > 0 else 0.0
            else:
                val = float(cum.iloc[sel])

            df_res.iloc[df_res.index.get_loc(date), pos] = val

        # annualize target (daily to yearly)
        try:
            annual_target = np.exp(float(target) * 252) - 1
        except Exception:
            annual_target = float(target) * 252

        labels[f"idx_{idx}"] = f"idx={idx} target={annual_target*100:.2f}%"

    # Save CSV
    csv_path = out_dir / "selected_portfolios_monthly.csv"
    df_res.to_csv(csv_path, index_label="date")

    # Plot
    plt.figure(figsize=(10, 5))
    for pos, idx in enumerate(indices):
        col = f"idx_{idx}"
        if col not in df_res:
            continue
        plt.plot(df_res.index, df_res[col], marker="o", label=labels.get(col, col))

    plt.title(f"Selected portfolios monthly snapshots {start} to {end}")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return")
    plt.legend()
    plt.grid(True)
    png_path = out_dir / f"selected_portfolios_monthly_{start}_to_{end}.png"
    plt.savefig(png_path, bbox_inches="tight")
    plt.close()

    return csv_path, png_path


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
    # Also create comparison plots for five portfolios: indices 0,12,25,37,49
    selected_indices = [0, 12, 25, 37, 49]
    plot_comparison_for_indices(df_weights, args.assets, args.out, windows, selected_indices)

    # Aggregate comparison across the whole test horizon
    aggregate_comparison(df_weights, args.assets, args.out, selected_indices)

    # Generate monthly snapshots and plot for selected portfolios
    monthly_csv, monthly_png = monthly_snapshots(
        df_weights, args.assets, args.out, selected_indices, start="2024-01-01", end="2025-06-30", freq="ME"
    )

    # Plot asset contributions for the selected portfolios and produce CSV summary
    contrib_df, contrib_csv = plot_asset_contributions(
        df_weights, args.assets, args.out, selected_indices, start="2024-03-01", end="2025-06-30"
    )

    print("Contributions summary CSV:", contrib_csv)

    print("Backtest finished. Summary and comparison plots saved to:", args.out)
    print("Monthly snapshots CSV:", monthly_csv)
    print("Monthly comparison PNG:", monthly_png)


if __name__ == "__main__":
    main()
