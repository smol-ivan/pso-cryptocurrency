import pandas as pd
import streamlit as st

from src.experiments import ExperimentResult
from src.ui import charts


def render_detail_tab(
    *,
    experiments: list[ExperimentResult],
    metrics_by_config: dict[str, pd.DataFrame],
    experiment_names: list[str],
    alpha: float,
    risk_column: str,
    risk_label: str,
) -> None:
    selected_config = st.selectbox(
        "Configuration",
        options=experiment_names,
        key="detail_config",
    )
    selected_experiment = next(
        experiment for experiment in experiments if experiment.config.name == selected_config
    )
    df_metrics = metrics_by_config[selected_experiment.config.name]
    fig_frontier = charts.build_frontier_chart(
        charts.FrontierChartData(
            df_metrics=df_metrics,
            risk_column=risk_column,
            risk_label=risk_label,
            title=f"Frontier - {selected_experiment.config.name}",
        )
    )
    st.plotly_chart(fig_frontier, width="stretch")

    df_display = pd.DataFrame(
        {
            f"CVaR {alpha * 100:.0f}%": df_metrics["cvar"] * 100,
            "Max Drawdown (%)": df_metrics["max_drawdown"] * 100,
            "Return (%)": df_metrics["mean_return"] * 100,
            "Volatility (%)": df_metrics["volatility"] * 100,
            "Sharpe Ratio": df_metrics["sharpe_ratio"],
            "Fitness": df_metrics["fitness"],
        }
    )
    st.dataframe(df_display, width="stretch")
