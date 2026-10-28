import pandas as pd
import streamlit as st

from src.experiments import ExperimentResult
from dashboards.legacy.ui import charts


def render_comparison_tab(
    *,
    experiments: list[ExperimentResult],
    metrics_by_config: dict[str, pd.DataFrame],
    seed_metrics_by_config: dict[str, pd.DataFrame] | None,
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

    if seed_metrics_by_config:
        st.subheader("Variabilidad entre semillas")
        max_points = max(
            int(metrics["portfolio_index"].max()) + 1
            for metrics in seed_metrics_by_config.values()
        )
        variability_index = st.selectbox(
            "Portfolio para comparar semillas",
            options=list(range(max_points)),
            format_func=lambda idx: f"Portfolio {idx + 1}",
            key="comparison_seed_variability_portfolio",
        )
        available_metrics = {
            name: metrics
            for name, metrics in seed_metrics_by_config.items()
            if variability_index in metrics["portfolio_index"].values
        }
        if available_metrics:
            fig_seed_fitness = charts.build_multi_seed_fitness_chart(
                charts.MultiSeedFitnessChartData(
                    seed_metrics_by_config=available_metrics,
                    portfolio_index=variability_index,
                    title=(
                        "Variabilidad del fitness final entre semillas "
                        f"- Portfolio {variability_index + 1}"
                    ),
                )
            )
            st.plotly_chart(fig_seed_fitness, width="stretch")

    available_histories = [
        experiment.frontier.convergence_histories
        for experiment in experiments
        if experiment.frontier.convergence_histories
    ]
    if available_histories:
        max_points = max(len(histories) for histories in available_histories)
        convergence_index = st.selectbox(
            "Portfolio para comparar convergencia",
            options=list(range(max_points)),
            format_func=lambda idx: f"Portfolio {idx + 1}",
            key="comparison_convergence_portfolio",
        )
        histories_by_config = {
            experiment.config.name: experiment.frontier.convergence_histories[
                convergence_index
            ]
            for experiment in experiments
            if experiment.frontier.convergence_histories
            and convergence_index < len(experiment.frontier.convergence_histories)
        }
        if histories_by_config:
            fig_convergence = charts.build_comparison_convergence_chart(
                charts.ComparisonConvergenceChartData(
                    histories_by_config=histories_by_config,
                )
            )
            st.plotly_chart(fig_convergence, width="stretch")
