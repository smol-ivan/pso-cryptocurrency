import pandas as pd
import streamlit as st

from src.controllers import run_analysis_pipeline
from src.finance import build_summary_dataframe
from src.models.state import ExperimentsPayload
from src.persistence import load_experiments
from src.ui.tabs import render_backtesting_tab, render_comparison_tab, render_detail_tab


OBJECTIVE_OPTIONS = ["CVaR", "MaxDrawdown"]
VELOCITY_OPTIONS = ["Inertia", "Constriction"]
TOPOLOGY_OPTIONS = ["Ring", "Global"]


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
        with st.form("config_form"):
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
            submitted = st.form_submit_button("▶️ Run experiments", use_container_width=True)

    if submitted:
        with st.spinner("Running experiments..."):
            pipeline_result = run_analysis_pipeline(
                assets=assets,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                selected_objectives=selected_objectives,
                selected_velocities=selected_velocities,
                selected_topologies=selected_topologies,
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

        if pipeline_result.validation_error:
            st.error(pipeline_result.validation_error)
            return
        if pipeline_result.error:
            st.error(f"Error while running experiments: {pipeline_result.error}")
            return
        if pipeline_result.backtesting_warning:
            st.warning(
                f"Automatic backtesting data could not be loaded: {pipeline_result.backtesting_warning}"
            )
        if pipeline_result.payload is None:
            st.error("Error while running experiments: missing analysis payload.")
            return

        st.session_state.experiments_payload = pipeline_result.payload
        st.success(f"Completed {pipeline_result.completed_experiments} experiment(s).")

    payload: ExperimentsPayload | dict[str, object] | None = st.session_state.get(
        "experiments_payload"
    )
    if payload is None:
        st.info("Run at least one experiment to see comparison and detailed analysis.")
        return
    if isinstance(payload, dict):
        payload = ExperimentsPayload.from_dict(payload)
        st.session_state.experiments_payload = payload
    if not isinstance(payload, ExperimentsPayload):
        st.error("Invalid experiments payload in session state.")
        return

    experiments = payload.experiments
    metrics_by_config = payload.metrics_by_config
    alpha = payload.alpha
    assets = payload.assets

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

    summary_df = build_summary_dataframe(
        experiments=experiments,
        metrics_by_config=metrics_by_config,
        comparison_mode=comparison_mode,
        fixed_portfolio_index=fixed_portfolio_index,
    )

    st.divider()
    tab_comparison, tab_detail, tab_backtesting = st.tabs(
        ["📊 Comparison", "🔎 Single configuration", "📉 Backtesting"]
    )

    with tab_comparison:
        render_comparison_tab(
            payload=payload,
            experiments=experiments,
            metrics_by_config=metrics_by_config,
            summary_df=summary_df,
            comparison_mode=comparison_mode,
            fixed_portfolio_index=fixed_portfolio_index,
            common_frontier_points=common_frontier_points,
            risk_column=risk_column,
            risk_label=risk_label,
            summary_risk_column=summary_risk_column,
        )

    with tab_detail:
        render_detail_tab(
            experiments=experiments,
            metrics_by_config=metrics_by_config,
            experiment_names=experiment_names,
            alpha=alpha,
            risk_column=risk_column,
            risk_label=risk_label,
        )

    with tab_backtesting:
        render_backtesting_tab(
            payload=payload,
            experiments=experiments,
            metrics_by_config=metrics_by_config,
            experiment_names=experiment_names,
            assets=assets,
            risk_column=risk_column,
        )


if __name__ == "__main__":
    main()
