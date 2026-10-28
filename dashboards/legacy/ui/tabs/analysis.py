import pandas as pd
import numpy as np
import streamlit as st

from src.experiments import ExperimentResult
from datetime import datetime

from src.finance import (
    annualized_return,
    build_seed_statistics_dataframe,
    build_weights_table,
    spaced_frontier_indices,
)
from src.models.state import ExperimentsPayload
from dashboards.legacy.ui import charts
from dashboards.legacy.ui.colors import get_crypto_colors


def render_analysis_tab(
    *,
    payload: ExperimentsPayload,
    experiments: list[ExperimentResult],
    metrics_by_config: dict[str, pd.DataFrame],
    experiment_names: list[str],
    assets: list[str],
    risk_column: str,
    risk_label: str,
) -> None:
    selected_config = st.selectbox(
        "Configuration",
        options=experiment_names,
        key="analysis_config",
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

    convergence_histories = selected_experiment.frontier.convergence_histories
    selected_seed_portfolio_index = 0
    if convergence_histories:
        st.subheader("Convergencia")
        convergence_index = st.selectbox(
            "Portfolio para la convergencia",
            options=list(range(len(convergence_histories))),
            format_func=lambda idx: f"Portfolio {idx + 1}",
            key=f"convergence_portfolio_{selected_config}",
        )
        selected_seed_portfolio_index = convergence_index
        fig_convergence = charts.build_convergence_chart(
            charts.ConvergenceChartData(
                convergence_history=convergence_histories[convergence_index],
                title=f"Convergencia - {selected_config} - Portfolio {convergence_index + 1}",
            )
        )
        st.plotly_chart(fig_convergence, width="stretch")

    seed_metrics = (payload.seed_metrics_by_config or {}).get(selected_config)
    seed_frontiers = selected_experiment.frontier.seed_results
    if seed_metrics is not None and seed_frontiers:
        st.subheader("Variabilidad entre semillas")
        if not convergence_histories:
            selected_seed_portfolio_index = st.selectbox(
                "Portfolio para analizar variabilidad",
                options=list(range(len(selected_experiment.frontier.weights))),
                format_func=lambda idx: f"Portfolio {idx + 1}",
                key=f"seed_variability_portfolio_{selected_config}",
            )
        selected_point_metrics = seed_metrics[
            seed_metrics["portfolio_index"] == selected_seed_portfolio_index
        ]
        fig_seed_fitness = charts.build_multi_seed_fitness_chart(
            charts.MultiSeedFitnessChartData(
                seed_metrics_by_config={selected_config: seed_metrics},
                portfolio_index=selected_seed_portfolio_index,
                title=(
                    f"Variabilidad - {selected_config} - "
                    f"Portfolio {selected_seed_portfolio_index + 1}"
                ),
            )
        )
        st.plotly_chart(fig_seed_fitness, width="stretch")
        fitness_values = selected_point_metrics["fitness"].to_numpy()
        fitness_mean = float(np.mean(fitness_values))
        if np.isclose(fitness_mean, 0.0):
            dispersion_label = "No disponible (media ≈ 0)"
        else:
            relative_dispersion = (
                (float(np.max(fitness_values)) - float(np.min(fitness_values)))
                / fitness_mean
            )
            dispersion_label = f"{relative_dispersion * 100:.2f}%"
        st.metric(
            "Dispersión relativa del fitness",
            dispersion_label,
            help="(máximo - mínimo) / |media| para las semillas del punto seleccionado.",
        )

    if seed_metrics is not None and seed_frontiers:
        st.caption(
            f"{len(seed_frontiers)} semillas por configuración; la semilla base se incrementa "
            "consecutivamente para cada réplica."
        )
        seed_stats = build_seed_statistics_dataframe(seed_metrics)
        display_stats = seed_stats.copy()
        display_stats.insert(0, "portfolio", display_stats.pop("portfolio_index") + 1)
        with st.expander("Ver estadísticas detalladas", expanded=False):
            st.dataframe(display_stats, width="stretch")

        with st.expander("Ver convergencia por semilla", expanded=False):
            seed_options = list(range(len(seed_frontiers)))
            histories_by_seed = {
                f"Semilla {seed if seed is not None else index + 1}": frontier.convergence_histories[
                    selected_seed_portfolio_index
                ]
                for index, (seed, frontier) in enumerate(
                    zip(
                        selected_experiment.frontier.seed_values or seed_options,
                        seed_frontiers,
                    )
                )
                if frontier.convergence_histories
                and selected_seed_portfolio_index < len(frontier.convergence_histories)
            }
            if histories_by_seed:
                fig_seed_convergence = charts.build_multi_seed_convergence_chart(
                    charts.MultiSeedConvergenceChartData(
                        histories_by_seed=histories_by_seed,
                        title=(
                            "Convergencia entre semillas - Portfolio "
                            f"{selected_seed_portfolio_index + 1}"
                        ),
                    )
                )
                st.plotly_chart(fig_seed_convergence, width="stretch")

    bt_returns_matrix = payload.bt_returns_matrix
    bt_returns_index = payload.bt_returns_index
    if bt_returns_matrix is not None and bt_returns_index is not None:
        st.subheader("📉 Backtesting")
        st.caption(f"Backtesting range: {payload.end_date} → {datetime.now().date().isoformat()}")

        default_count = min(5, len(selected_experiment.frontier.weights))
        default_selected_indices = spaced_frontier_indices(
            total_points=len(selected_experiment.frontier.weights),
            count=default_count,
        )
        selected_indices = st.multiselect(
            "Portfolios",
            options=list(range(len(selected_experiment.frontier.weights))),
            default=default_selected_indices,
            format_func=lambda idx: (
                f"Portfolio {idx + 1} | "
                f"ret={df_metrics.iloc[idx]['mean_return']:.4f}, "
                f"{risk_column}={df_metrics.iloc[idx][risk_column]:.4f}"
            ),
            key=f"bt_multiselect_{selected_config}",
        )

        if selected_indices:
            crypto_colors = get_crypto_colors(assets)
            st.subheader("Asset color legend")
            cols_legend = st.columns(len(assets))
            for col_idx, asset in enumerate(assets):
                with cols_legend[col_idx]:
                    color = crypto_colors[asset]
                    st.markdown(
                        f"<div style='background-color:{color}; padding:10px; border-radius:5px; text-align:center'>"
                        f"<b style='color:white'>{asset}</b></div>",
                        unsafe_allow_html=True,
                    )

            st.divider()
            st.subheader("Portfolio composition")
            cols_pie = st.columns(2)
            for col_idx, idx in enumerate(selected_indices):
                with cols_pie[col_idx % 2]:
                    colors = [crypto_colors[asset] for asset in assets]
                    fig_pie = charts.build_portfolio_pie_chart(
                        charts.PortfolioPieChartData(
                            assets=assets,
                            weights=selected_experiment.frontier.weights[idx],
                            colors=colors,
                            portfolio_number=idx + 1,
                        )
                    )
                    st.plotly_chart(fig_pie, width="stretch")

                    ret_daily = df_metrics.iloc[idx]["mean_return"]
                    ret_annual = annualized_return(ret_daily)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Daily return", f"{ret_daily * 100:.3f}%")
                    with col_b:
                        st.metric("Annualized return", f"{ret_annual * 100:.2f}%")

            st.divider()
            st.subheader("Portfolio weights")
            df_weights = build_weights_table(
                assets=assets,
                weights=selected_experiment.frontier.weights,
                selected_indices=selected_indices,
            )
            st.dataframe((df_weights * 100).round(2).astype(str) + "%", width="stretch")

            st.subheader("Cumulative return")
            fig_performance = charts.build_backtesting_chart(
                charts.BacktestingChartData(
                    returns_matrix=bt_returns_matrix,
                    returns_index=bt_returns_index,
                    weights=selected_experiment.frontier.weights,
                    selected_indices=selected_indices,
                )
            )
            st.plotly_chart(fig_performance, width="stretch")
