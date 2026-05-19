import pandas as pd
import streamlit as st

from src.experiments import ExperimentResult
from datetime import datetime

from src.finance import annualized_return, build_weights_table, spaced_frontier_indices
from src.models.state import ExperimentsPayload
from src.ui import charts
from src.ui.colors import get_crypto_colors


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
