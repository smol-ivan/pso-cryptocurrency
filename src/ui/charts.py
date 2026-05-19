from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative


@dataclass
class ComparisonChartsData:
    summary_df: pd.DataFrame
    risk_column: str
    risk_label: str
    yaxis_title: str


@dataclass
class MultiPointChartsData:
    points_df: pd.DataFrame
    risk_column: str
    risk_label: str


@dataclass
class CrossConfigChartsData:
    returns_matrix: np.ndarray
    returns_index: pd.Index
    config_names: list[str]
    weights_by_config: list[np.ndarray]


@dataclass
class FrontierChartData:
    df_metrics: pd.DataFrame
    risk_column: str
    risk_label: str
    title: str = "Frontera Eficiente (Risk vs Return)"


@dataclass
class ComparisonFrontierChartData:
    experiments: list
    metrics_by_config: dict[str, pd.DataFrame]
    risk_column: str
    risk_label: str
    title: str = "Fronteras eficientes por configuración"


@dataclass
class PortfolioPieChartData:
    assets: list[str]
    weights: np.ndarray
    colors: list[str]
    portfolio_number: int


@dataclass
class BacktestingChartData:
    returns_matrix: np.ndarray
    returns_index: pd.Index
    weights: list[np.ndarray]
    selected_indices: list[int]


def build_comparison_charts(data: ComparisonChartsData) -> go.Figure:
    return _build_experiment_comparison_figure(
        summary_df=data.summary_df,
        risk_column=data.risk_column,
        risk_label=data.risk_label,
        yaxis_title=data.yaxis_title,
    )


def build_multi_point_charts(data: MultiPointChartsData) -> go.Figure:
    return _build_multi_point_comparison_figure(
        points_df=data.points_df,
        risk_column=data.risk_column,
        risk_label=data.risk_label,
    )


def build_cross_config_charts(data: CrossConfigChartsData) -> go.Figure:
    return _build_cross_config_returns_figure(
        returns_matrix=data.returns_matrix,
        returns_index=data.returns_index,
        config_names=data.config_names,
        weights_by_config=data.weights_by_config,
    )


def build_frontier_chart(data: FrontierChartData) -> go.Figure:
    return _build_frontier_figure(
        df_metrics=data.df_metrics,
        risk_column=data.risk_column,
        risk_label=data.risk_label,
        title=data.title,
    )


def build_comparison_frontier_chart(data: ComparisonFrontierChartData) -> go.Figure:
    return _build_comparison_frontier_figure(
        experiments=data.experiments,
        metrics_by_config=data.metrics_by_config,
        risk_column=data.risk_column,
        risk_label=data.risk_label,
        title=data.title,
    )


def build_portfolio_pie_chart(data: PortfolioPieChartData) -> go.Figure:
    return _build_portfolio_pie_figure(
        assets=data.assets,
        weights=data.weights,
        colors=data.colors,
        portfolio_number=data.portfolio_number,
    )


def build_backtesting_chart(data: BacktestingChartData) -> go.Figure:
    return _build_backtesting_returns_figure(
        returns_matrix=data.returns_matrix,
        returns_index=data.returns_index,
        weights=data.weights,
        selected_indices=data.selected_indices,
    )


def _build_frontier_figure(
    df_metrics: pd.DataFrame,
    risk_column: str,
    risk_label: str,
    title: str,
) -> go.Figure:
    chart_df = df_metrics.sort_values(by=risk_column).reset_index(drop=True)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df[risk_column],
            y=chart_df["mean_return"],
            mode="markers+lines",
            name="Frontera Eficiente",
            marker=dict(
                size=8,
                color=chart_df["sharpe_ratio"],
                colorscale="Viridis",
                showscale=True,
            ),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=risk_label,
        yaxis_title="Retorno Esperado",
        hovermode="closest",
    )
    return fig


def _build_experiment_comparison_figure(
    summary_df: pd.DataFrame, risk_column: str, risk_label: str, yaxis_title: str
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=summary_df[risk_column],
            y=summary_df["selected_mean_return"],
            mode="markers",
            marker=dict(
                size=12,
                color=summary_df["selected_sharpe_ratio"],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Sharpe"),
            ),
            name="Configuraciones",
            customdata=summary_df[["name", "objective", "velocity", "topology"]],
            hovertemplate=(
                "Config: %{customdata[0]}<br>"
                "Objective: %{customdata[1]}<br>"
                "Velocity: %{customdata[2]}<br>"
                "Topology: %{customdata[3]}<br>"
                f"{risk_label}: %{{x:.6f}}<br>"
                "Return: %{y:.6f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Comparativa de configuraciones",
        xaxis_title=risk_label,
        yaxis_title=yaxis_title,
        hovermode="closest",
    )
    return fig


def _build_comparison_frontier_figure(
    experiments: list,
    metrics_by_config: dict[str, pd.DataFrame],
    risk_column: str,
    risk_label: str,
    title: str,
) -> go.Figure:
    fig = go.Figure()
    colors = qualitative.Plotly

    for index, experiment in enumerate(experiments):
        config_name = experiment.config.name
        config_df = metrics_by_config[config_name].copy()
        config_df = config_df.assign(portfolio_index=np.arange(1, len(config_df) + 1))
        config_df = config_df.sort_values(by=risk_column).reset_index(drop=True)
        color = colors[index % len(colors)]

        fig.add_trace(
            go.Scatter(
                x=config_df[risk_column],
                y=config_df["mean_return"],
                mode="lines+markers",
                name=config_name,
                line=dict(color=color, width=2),
                marker=dict(color=color, size=6),
                customdata=config_df[["portfolio_index"]],
                hovertemplate=(
                    "Configuración: " + config_name + "<br>"
                    f"{risk_label}: %{{x:.6f}}<br>"
                    "Retorno esperado: %{y:.6f}<br>"
                    "Portafolio: %{customdata[0]}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title=risk_label,
        yaxis_title="Retorno esperado",
        hovermode="closest",
        legend_title_text="Configuración",
    )
    return fig


def _build_multi_point_comparison_figure(
    points_df: pd.DataFrame,
    risk_column: str,
    risk_label: str,
) -> go.Figure:
    fig = go.Figure()
    for config_name, config_df in points_df.groupby("name"):
        config_df = config_df.sort_values(by="portfolio_index")
        fig.add_trace(
            go.Scatter(
                x=config_df[risk_column],
                y=config_df["mean_return"],
                mode="markers+lines",
                name=config_name,
                customdata=config_df[["portfolio_index", "target_return"]],
                hovertemplate=(
                    "Config: " + config_name + "<br>"
                    "Portfolio index: %{customdata[0]}<br>"
                    "Target return: %{customdata[1]:.6f}<br>"
                    f"{risk_label}: %{{x:.6f}}<br>"
                    "Mean return: %{y:.6f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Comparativa multi-punto por configuración",
        xaxis_title=risk_label,
        yaxis_title="Mean return",
        hovermode="closest",
    )
    return fig


def _build_cross_config_returns_figure(
    returns_matrix: np.ndarray,
    returns_index: pd.Index,
    config_names: list[str],
    weights_by_config: list[np.ndarray],
) -> go.Figure:
    fig = go.Figure()
    for config_name, weights in zip(config_names, weights_by_config):
        portfolio_returns = returns_matrix @ weights
        cumulative_returns = np.cumprod(1 + portfolio_returns) - 1
        fig.add_trace(
            go.Scatter(
                x=returns_index,
                y=cumulative_returns * 100,
                mode="lines",
                name=config_name,
                hovertemplate="Fecha: %{x|%Y-%m-%d}<br>Retorno: %{y:.2f}%<extra></extra>",
            )
        )

    fig.update_layout(
        title="Comparativa de rendimiento acumulado entre configuraciones",
        xaxis_title="Fecha",
        yaxis_title="Retorno acumulado (%)",
        hovermode="x unified",
        height=500,
    )
    return fig


def _build_portfolio_pie_figure(
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


def _build_backtesting_returns_figure(
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
