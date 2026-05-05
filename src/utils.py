from typing import List

import numpy as np
import pandas as pd
import yfinance as yf


def load_crypto_returns(
    assets: List[str], start: str = "2020-01-01", end: str = "2024-01-01", interval: str = "1d"
):
    """Get historical data of cryptocurrencies"""
    close_prices = yf.download(
        assets, start=start, end=end, interval=interval, progress=False
    )["Close"]

    if close_prices.empty:
        raise ValueError("No price data was downloaded for the selected assets and dates.")

    returns = np.log(close_prices / close_prices.shift(1)).dropna()
    if isinstance(returns, pd.Series):
        asset_name = assets[0] if assets else "asset"
        returns = returns.to_frame(name=asset_name)

    returns_matrix = returns.values  # (T x N)
    mean_return = returns_matrix.mean(axis=0)

    return mean_return, returns_matrix, returns.index
