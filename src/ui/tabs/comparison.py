import pandas as pd
import streamlit as st

from src.experiments import ExperimentResult
from src.ui import charts


def render_comparison_tab(
    *,
    experiments: list[ExperimentResult],
    metrics_by_config: dict[str, pd.DataFrame],
    risk_column: str,
    risk_label: str,
) -> None:
    st.caption(
        "Each curve represents the efficient frontier found by one PSO configuration."
    )

    fig_comparison = charts.build_comparison_frontier_chart(
        charts.ComparisonFrontierChartData(
            experiments=experiments,
            metrics_by_config=metrics_by_config,
            risk_column=risk_column,
            risk_label=risk_label,
        )
    )
    st.plotly_chart(fig_comparison, width="stretch")
