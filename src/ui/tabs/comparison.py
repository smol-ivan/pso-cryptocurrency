import pandas as pd
import streamlit as st

from src.experiments import ExperimentResult
from src.finance import build_multi_point_dataframe
from src.models.state import ExperimentsPayload
from src.ui import charts


def render_comparison_tab(
    *,
    payload: ExperimentsPayload,
    experiments: list[ExperimentResult],
    metrics_by_config: dict[str, pd.DataFrame],
    summary_df: pd.DataFrame,
    comparison_mode: str,
    fixed_portfolio_index: int,
    common_frontier_points: int,
    risk_column: str,
    risk_label: str,
    summary_risk_column: str,
) -> None:
    if comparison_mode == "Fixed frontier index":
        st.caption(f"Comparing all configurations at portfolio index #{fixed_portfolio_index}.")
        comparison_y_label = "Mean return (fixed frontier index)"
    else:
        comparison_y_label = "Mean return (portfolio with best Sharpe)"

    fig_comparison = charts.build_comparison_charts(
        charts.ComparisonChartsData(
            summary_df=summary_df,
            risk_column=summary_risk_column,
            risk_label=risk_label,
            yaxis_title=comparison_y_label,
        )
    )
    st.plotly_chart(fig_comparison, width="stretch")
    summary_display = summary_df[
        [
            "name",
            "objective",
            "velocity",
            "topology",
            "selected_portfolio",
            "selected_target_return",
            "selected_mean_return",
            "selected_cvar",
            "selected_max_drawdown",
            "selected_volatility",
            "selected_sharpe_ratio",
        ]
    ].copy()
    summary_display.columns = [
        "Configuration",
        "Objective",
        "Velocity",
        "Topology",
        "Portfolio #",
        "Target return",
        "Mean return",
        "CVaR",
        "Max drawdown",
        "Volatility",
        "Sharpe",
    ]
    st.dataframe(summary_display.round(6), width="stretch")

    default_point_selection = sorted(
        {
            1,
            max(1, common_frontier_points // 2),
            common_frontier_points,
        }
    )
    selected_point_indices = st.multiselect(
        "Extra comparison points (same indices across configurations)",
        options=list(range(1, common_frontier_points + 1)),
        default=default_point_selection,
        help=(
            "Choose 2-3 (or more) frontier indices to compare each configuration "
            "with multiple representative points."
        ),
    )
    if selected_point_indices:
        points_df = build_multi_point_dataframe(
            experiments=experiments,
            metrics_by_config=metrics_by_config,
            selected_point_indices=selected_point_indices,
        )
        fig_multi_point = charts.build_multi_point_charts(
            charts.MultiPointChartsData(
                points_df=points_df,
                risk_column=risk_column,
                risk_label=risk_label,
            )
        )
        st.plotly_chart(fig_multi_point, width="stretch")

    bt_returns_matrix = payload.bt_returns_matrix
    bt_returns_index = payload.bt_returns_index
    if bt_returns_matrix is not None and bt_returns_index is not None:
        st.subheader("📈 Cross-configuration backtesting")
        st.caption(
            "One line per configuration, using the portfolio currently selected by the comparison mode."
        )
        selected_config_names = summary_df["name"].tolist()
        weights_by_config = []
        experiments_by_name = {experiment.config.name: experiment for experiment in experiments}
        for row in summary_df.itertuples(index=False):
            selected_idx = int(row.selected_portfolio) - 1
            selected_experiment = experiments_by_name[row.name]
            weights_by_config.append(selected_experiment.frontier.weights[selected_idx])

        fig_cross_config = charts.build_cross_config_charts(
            charts.CrossConfigChartsData(
                returns_matrix=bt_returns_matrix,
                returns_index=bt_returns_index,
                config_names=selected_config_names,
                weights_by_config=weights_by_config,
            )
        )
        st.plotly_chart(fig_cross_config, width="stretch")
