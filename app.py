from datetime import datetime
from itertools import product

import pandas as pd
import streamlit as st

from src.experiments import ExperimentConfig, run_experiments
from src.models.fitness_function import CVaR, MaxDrawdown
from src.models.topology import GlobalTopology, RingTopology
from src.models.velocity_model import Constriction, Inertia
from src.persistence import load_experiments, save_experiments
from src.run_pso import PSOInputData
from src.ui.charts import (
    build_backtesting_returns_figure,
    build_cross_config_returns_figure,
    build_experiment_comparison_figure,
    build_frontier_figure,
    build_multi_point_comparison_figure,
    build_portfolio_pie_figure,
)
from src.ui.colors import get_crypto_colors
from src.ui.metrics import (
    annualized_return,
    build_metrics_dataframe,
    build_weights_table,
    spaced_frontier_indices,
)
from src.utils import load_crypto_returns


OBJECTIVE_OPTIONS = ["CVaR", "MaxDrawdown"]
VELOCITY_OPTIONS = ["Inertia", "Constriction"]
TOPOLOGY_OPTIONS = ["Ring", "Global"]


def _build_experiment_configs(
    selected_objectives: list[str],
    selected_velocities: list[str],
    selected_topologies: list[str],
    *,
    alpha: float,
    penalty: float,
    c1: float,
    c2: float,
    inertia: float,
    num_points: int,
    n_swarm: int,
    epsilon: float,
    base_seed: int | None,
) -> list[ExperimentConfig]:
    configs: list[ExperimentConfig] = []

    for config_index, (objective_name, velocity_name, topology_name) in enumerate(
        product(
        selected_objectives, selected_velocities, selected_topologies
        )
    ):
        if objective_name == "CVaR":
            fitness_function = CVaR(alpha=alpha, penalty=penalty)
        else:
            fitness_function = MaxDrawdown(penalty=penalty)

        if velocity_name == "Inertia":
            velocity_model = Inertia(c1=c1, c2=c2, inertia=inertia)
        else:
            velocity_model = Constriction(c1=c1, c2=c2)

        topology = RingTopology(k_neighbors=1) if topology_name == "Ring" else GlobalTopology()
        config_name = f"{objective_name} | {velocity_name} | {topology_name}"

        configs.append(
            ExperimentConfig(
                name=config_name,
                objective_name=objective_name,
                velocity_name=velocity_name,
                topology_name=topology_name,
                fitness_function=fitness_function,
                velocity_model=velocity_model,
                topology=topology,
                num_points=num_points,
                n_swarm=n_swarm,
                epsilon=epsilon,
                seed=None if base_seed is None else base_seed + config_index,
            )
        )

    return configs


def _risk_axes(alpha: float) -> dict[str, tuple[str, str, str]]:
    return {
        "CVaR": ("cvar", f"CVaR {alpha * 100:.0f}%", "selected_cvar"),
        "Max Drawdown": ("max_drawdown", "Max Drawdown", "selected_max_drawdown"),
        "Volatility": ("volatility", "Volatility", "selected_volatility"),
    }


def main():
    st.set_page_config(page_title="PSO Crypto", layout="wide")
    st.title("🚀 PSO Cryptocurrency - Experiments & Comparison")

    if "experiments_payload" not in st.session_state:
        persisted = load_experiments()
        if persisted is not None:
            st.session_state.experiments_payload = persisted

    with st.sidebar:
        st.header("⚙️ Configuration")

        assets_default = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]
        assets = st.multiselect(
            "Assets",
            options=assets_default,
            default=assets_default,
        )

        st.subheader("Market data")
        start_date = st.date_input("Start date", value=pd.to_datetime("2020-01-01"))
        end_date = st.date_input("End date", value=pd.to_datetime("2024-01-01"))
        interval = st.selectbox("Interval", options=["1d", "1wk", "1mo"], index=0)

        st.subheader("PSO")
        num_points = st.slider("Frontier points", 10, 100, 30)
        n_swarm = st.slider("Swarm size", 20, 200, 100)
        epsilon = st.number_input("Convergence epsilon", value=1e-5, format="%e")
        random_seed_enabled = st.checkbox("Use reproducible seeds", value=True)
        base_seed = st.number_input(
            "Base seed",
            min_value=0,
            max_value=10_000_000,
            value=42,
            step=1,
            disabled=not random_seed_enabled,
        )

        st.subheader("Objectives")
        selected_objectives = st.multiselect(
            "Fitness functions",
            options=OBJECTIVE_OPTIONS,
            default=["CVaR"],
        )
        alpha = st.slider("CVaR alpha", 0.80, 0.99, 0.95)
        penalty = st.number_input(
            "Target penalty",
            min_value=1.0,
            max_value=5000.0,
            value=500.0,
            step=1.0,
        )

        st.subheader("Velocity models")
        selected_velocities = st.multiselect(
            "Velocity",
            options=VELOCITY_OPTIONS,
            default=["Inertia"],
        )
        c1 = st.slider("c1", 0.5, 3.0, 1.7)
        c2 = st.slider("c2", 0.5, 3.0, 1.7)
        inertia = st.slider("inertia (w)", 0.4, 1.0, 0.8)

        st.subheader("Topologies")
        selected_topologies = st.multiselect(
            "Topology",
            options=TOPOLOGY_OPTIONS,
            default=["Ring"],
        )

    if st.button("▶️ Run experiments", width="stretch"):
        if not assets:
            st.error("Select at least one asset.")
            return
        if start_date >= end_date:
            st.error("Start date must be before end date.")
            return
        if not selected_objectives or not selected_velocities or not selected_topologies:
            st.error("Select at least one option in objective, velocity and topology.")
            return
        if "Constriction" in selected_velocities and (c1 + c2) <= 4:
            st.error("Constriction requires c1 + c2 > 4.")
            return

        with st.spinner("Running experiments..."):
            try:
                mean_return, returns_matrix, returns_index = load_crypto_returns(
                    assets,
                    start=start_date.isoformat(),
                    end=end_date.isoformat(),
                    interval=interval,
                )
                input_data = PSOInputData(
                    mean_return=mean_return,
                    returns_matrix=returns_matrix,
                )
                configs = _build_experiment_configs(
                    selected_objectives,
                    selected_velocities,
                    selected_topologies,
                    alpha=alpha,
                    penalty=penalty,
                    c1=c1,
                    c2=c2,
                    inertia=inertia,
                    num_points=num_points,
                    n_swarm=n_swarm,
                    epsilon=epsilon,
                    base_seed=int(base_seed) if random_seed_enabled else None,
                )
                experiments = run_experiments(input_data=input_data, experiment_configs=configs)

                metrics_by_config: dict[str, pd.DataFrame] = {}
                for experiment in experiments:
                    metrics_by_config[experiment.config.name] = build_metrics_dataframe(
                        returns_matrix=returns_matrix,
                        weights_list=experiment.frontier.weights,
                        cvar_alpha=alpha,
                        fitness_values=experiment.frontier.best_fitnesses,
                    )

                bt_returns_matrix = None
                bt_returns_index = None
                try:
                    backtest_start = end_date
                    backtest_end = datetime.now().date()
                    if backtest_start < backtest_end:
                        _, bt_returns_matrix, bt_returns_index = load_crypto_returns(
                            assets,
                            start=backtest_start.isoformat(),
                            end=backtest_end.isoformat(),
                            interval=interval,
                        )
                except Exception as error:
                    st.warning(f"Automatic backtesting data could not be loaded: {error}")

                payload = {
                    "assets": assets,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "interval": interval,
                    "alpha": alpha,
                    "returns_matrix": returns_matrix,
                    "returns_index": returns_index,
                    "experiments": experiments,
                    "metrics_by_config": metrics_by_config,
                    "bt_returns_matrix": bt_returns_matrix,
                    "bt_returns_index": bt_returns_index,
                }
                st.session_state.experiments_payload = payload
                save_experiments(payload)
                st.success(f"Completed {len(experiments)} experiment(s).")
            except Exception as error:
                st.error(f"Error while running experiments: {error}")

    payload = st.session_state.get("experiments_payload")
    if payload is None:
        st.info("Run at least one experiment to see comparison and detailed analysis.")
        return

    experiments = payload["experiments"]
    metrics_by_config = payload["metrics_by_config"]
    alpha = payload["alpha"]
    assets = payload["assets"]

    risk_options = _risk_axes(alpha)
    selected_risk = st.selectbox(
        "Comparison risk metric",
        options=list(risk_options.keys()),
        help="This changes the X-axis metric used for comparison and individual frontier views.",
    )
    risk_column, risk_label, summary_risk_column = risk_options[selected_risk]

    experiment_names = [experiment.config.name for experiment in experiments]
    common_frontier_points = min(len(experiment.frontier.weights) for experiment in experiments)
    comparison_mode = st.radio(
        "Comparison portfolio selector",
        options=["Best Sharpe", "Fixed frontier index"],
        horizontal=True,
        help=(
            "Best Sharpe picks one representative portfolio per configuration. "
            "Fixed frontier index compares the same frontier position across all configurations."
        ),
    )
    fixed_portfolio_index = 1
    if comparison_mode == "Fixed frontier index":
        default_mid_index = max(1, (common_frontier_points // 2) + 1)
        fixed_portfolio_index = st.slider(
            "Frontier portfolio index",
            min_value=1,
            max_value=common_frontier_points,
            value=default_mid_index,
        )

    summary_rows = []
    for experiment in experiments:
        df = metrics_by_config[experiment.config.name]
        if comparison_mode == "Best Sharpe":
            selected_idx = int(df["sharpe_ratio"].idxmax())
        else:
            selected_idx = fixed_portfolio_index - 1

        summary_rows.append(
            {
                "name": experiment.config.name,
                "objective": experiment.config.objective_name,
                "velocity": experiment.config.velocity_name,
                "topology": experiment.config.topology_name,
                "selected_portfolio": selected_idx + 1,
                "selected_target_return": float(
                    experiment.frontier.target_values[selected_idx]
                ),
                "selected_mean_return": float(df.loc[selected_idx, "mean_return"]),
                "selected_cvar": float(df.loc[selected_idx, "cvar"]),
                "selected_max_drawdown": float(df.loc[selected_idx, "max_drawdown"]),
                "selected_volatility": float(df.loc[selected_idx, "volatility"]),
                "selected_sharpe_ratio": float(df.loc[selected_idx, "sharpe_ratio"]),
                "selected_fitness": float(df.loc[selected_idx, "fitness"]),
            }
        )
    summary_df = pd.DataFrame(summary_rows)

    st.divider()
    tab_comparison, tab_detail, tab_backtesting = st.tabs(
        ["📊 Comparison", "🔎 Single configuration", "📉 Backtesting"]
    )

    with tab_comparison:
        if comparison_mode == "Fixed frontier index":
            st.caption(
                f"Comparing all configurations at portfolio index #{fixed_portfolio_index}."
            )
            comparison_y_label = "Mean return (fixed frontier index)"
        else:
            comparison_y_label = "Mean return (portfolio with best Sharpe)"

        fig_comparison = build_experiment_comparison_figure(
            summary_df=summary_df,
            risk_column=summary_risk_column,
            risk_label=risk_label,
            yaxis_title=comparison_y_label,
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
            points_rows = []
            for experiment in experiments:
                df_metrics = metrics_by_config[experiment.config.name]
                for point_index in selected_point_indices:
                    idx = point_index - 1
                    points_rows.append(
                        {
                            "name": experiment.config.name,
                            "portfolio_index": point_index,
                            "target_return": float(experiment.frontier.target_values[idx]),
                            "mean_return": float(df_metrics.loc[idx, "mean_return"]),
                            "cvar": float(df_metrics.loc[idx, "cvar"]),
                            "max_drawdown": float(df_metrics.loc[idx, "max_drawdown"]),
                            "volatility": float(df_metrics.loc[idx, "volatility"]),
                        }
                    )

            points_df = pd.DataFrame(points_rows)
            fig_multi_point = build_multi_point_comparison_figure(
                points_df=points_df,
                risk_column=risk_column,
                risk_label=risk_label,
            )
            st.plotly_chart(fig_multi_point, width="stretch")

        bt_returns_matrix = payload.get("bt_returns_matrix")
        bt_returns_index = payload.get("bt_returns_index")
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

            fig_cross_config = build_cross_config_returns_figure(
                returns_matrix=bt_returns_matrix,
                returns_index=bt_returns_index,
                config_names=selected_config_names,
                weights_by_config=weights_by_config,
            )
            st.plotly_chart(fig_cross_config, width="stretch")

    with tab_detail:
        selected_config = st.selectbox(
            "Configuration",
            options=experiment_names,
            key="detail_config",
        )
        selected_experiment = next(
            experiment for experiment in experiments if experiment.config.name == selected_config
        )
        df_metrics = metrics_by_config[selected_experiment.config.name]
        fig_frontier = build_frontier_figure(
            df_metrics=df_metrics,
            risk_column=risk_column,
            risk_label=risk_label,
            title=f"Frontier - {selected_experiment.config.name}",
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

    with tab_backtesting:
        selected_config = st.selectbox(
            "Configuration for backtesting",
            options=experiment_names,
            key="backtesting_config",
        )
        selected_experiment = next(
            experiment for experiment in experiments if experiment.config.name == selected_config
        )
        df_metrics = metrics_by_config[selected_experiment.config.name]

        bt_returns_matrix = payload.get("bt_returns_matrix")
        bt_returns_index = payload.get("bt_returns_index")
        if bt_returns_matrix is None or bt_returns_index is None:
            st.info("No automatic backtesting data available for this run.")
            return

        st.caption(
            f"Backtesting range: {payload['end_date']} → {datetime.now().date().isoformat()}"
        )
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

        if not selected_indices:
            return

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
                fig_pie = build_portfolio_pie_figure(
                    assets=assets,
                    weights=selected_experiment.frontier.weights[idx],
                    colors=colors,
                    portfolio_number=idx + 1,
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
        fig_performance = build_backtesting_returns_figure(
            returns_matrix=bt_returns_matrix,
            returns_index=bt_returns_index,
            weights=selected_experiment.frontier.weights,
            selected_indices=selected_indices,
        )
        st.plotly_chart(fig_performance, width="stretch")


if __name__ == "__main__":
    main()
