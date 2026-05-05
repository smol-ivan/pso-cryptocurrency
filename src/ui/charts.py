import numpy as np
import pandas as pd
import plotly.graph_objects as go


def build_frontier_figure(df_metrics: pd.DataFrame, alpha: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_metrics["cvar"],
            y=df_metrics["mean_return"],
            mode="markers+lines",
            name="Frontera Eficiente",
            marker=dict(
                size=8,
                color=df_metrics["sharpe_ratio"],
                colorscale="Viridis",
                showscale=True,
            ),
        )
    )
    fig.update_layout(
        title="Frontera Eficiente (Risk vs Return)",
        xaxis_title=f"CVaR {alpha * 100}%",
        yaxis_title="Retorno Esperado",
        hovermode="closest",
    )
    return fig


def build_portfolio_pie_figure(
    assets: list[str], weights: np.ndarray, colors: list[str], portfolio_number: int
) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Pie(
                labels=assets,
                values=weights,
                marker=dict(colors=colors),
                textposition="outside",
                showlegend=False,
            )
        ]
    )
    fig.update_layout(
        height=450,
        title=dict(
            text=f"Portafolio {portfolio_number}",
            x=0.5,
            xanchor="center",
            y=0.0,
            yanchor="bottom",
        ),
        margin=dict(b=80),
    )
    return fig


def build_backtesting_returns_figure(
    returns_matrix: np.ndarray,
    returns_index: pd.Index,
    weights: list[np.ndarray],
    selected_indices: list[int],
) -> go.Figure:
    fig = go.Figure()
    for idx in selected_indices:
        portfolio_returns = returns_matrix @ weights[idx]
        cumulative_returns = np.cumprod(1 + portfolio_returns) - 1
        fig.add_trace(
            go.Scatter(
                x=returns_index,
                y=cumulative_returns * 100,
                mode="lines",
                name=f"Portafolio {idx + 1}",
                hovertemplate="Fecha: %{x|%Y-%m-%d}<br>Retorno: %{y:.2f}%<extra></extra>",
            )
        )

    fig.update_layout(
        title="Rendimiento en Backtesting (Retorno Acumulado %)",
        xaxis_title="Fecha",
        yaxis_title="Retorno Acumulado (%)",
        hovermode="x unified",
        height=500,
    )
    return fig
