import numpy as np
import yfinance as yf

try:
    from arch import arch_model
except ImportError:  # pragma: no cover - se valida en tiempo de ejecucion
    arch_model = None


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


def simulate_garch_returns(returns_matrix, n_scenarios=5000):
    """
    Ajusta un modelo GARCH(1,1) por activo y simula escenarios de retornos.

    Args:
        returns_matrix: matriz historica (T x N)
        n_scenarios: numero de escenarios simulados por activo

    Returns:
        mean_return: vector (N,)
        simulated_returns: matriz simulada (S x N)
    """
    if arch_model is None:
        raise ImportError(
            "Falta la dependencia 'arch'. Instala con: pip install arch"
        )

    n_assets = returns_matrix.shape[1]
    simulated_returns = np.zeros((n_scenarios, n_assets))

    # `arch` trabaja mejor en escala de porcentaje
    scaled_returns = returns_matrix * 100.0

    for i in range(n_assets):
        asset_returns = scaled_returns[:, i]

        model = arch_model(
            asset_returns,
            mean="Constant",
            vol="GARCH",
            p=1,
            q=1,
            dist="normal",
            rescale=False,
        )
        fitted = model.fit(disp="off")
        forecast = fitted.forecast(horizon=1, method="simulation", simulations=n_scenarios)

        # Simulaciones para t+1 en porcentaje, se vuelve a escala decimal
        scenario_values = forecast.simulations.values[-1, :, 0] / 100.0

        # Guardrail: evitar escenarios extremos inestables del ajuste GARCH
        # que distorsionan objetivo diario y su anualización en backtest.
        hist = returns_matrix[:, i]
        q01, q99 = np.quantile(hist, [0.01, 0.99])
        band = 3.0 * (q99 - q01)
        lower = q01 - band
        upper = q99 + band
        scenario_values = np.clip(scenario_values, lower, upper)

        simulated_returns[:, i] = scenario_values

    mean_return = simulated_returns.mean(axis=0)
    return mean_return, simulated_returns
