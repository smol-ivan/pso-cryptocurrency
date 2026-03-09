import numpy as np
import yfinance as yf


def load_crypto_returns(
    assets,
    start="2020-01-01",
    end="2024-01-01",
    interval="1d",
):
    """
    Descarga precios de Yahoo Finance y calcula retornos logarítmicos.

    Returns:
        mean_return: vector (N,)
        returns_matrix: matriz (T x N)
    """

    # Descargar precios
    data = yf.download(
        assets,
        start=start,
        end=end,
        interval=interval,
        progress=False,
    )["Close"]

    # Calcular retornos log
    returns = np.log(data / data.shift(1)).dropna()

    returns_matrix = returns.values  # (T x N)
    mean_return = returns_matrix.mean(axis=0)

    return mean_return, returns_matrix
