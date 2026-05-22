import pandas as pd
import streamlit as st
from datetime import datetime

from src.controllers import run_analysis_pipeline
from src.models.state import ExperimentsPayload
from src.persistence import load_experiments, export_payload_to_bytes, import_payload_from_bytes
from src.ui.tabs import render_analysis_tab, render_comparison_tab


OBJECTIVE_OPTIONS = ["CVaR", "MaxDrawdown"]
VELOCITY_OPTIONS = ["Inertia", "Constriction"]
TOPOLOGY_OPTIONS = ["Ring", "Global"]


def _risk_axes(alpha: float) -> dict[str, tuple[str, str, str]]:
    return {
        "CVaR": ("cvar", f"CVaR {alpha * 100:.0f}%", "selected_cvar"),
        "Max Drawdown": ("max_drawdown", "Max Drawdown", "selected_max_drawdown"),
        "Desviación estándar": (
            "volatility",
            "Desviación estándar",
            "selected_volatility",
        ),
    }


def main():
    st.set_page_config(page_title="PSO Crypto", layout="wide")
    st.title("🚀 PSO Cryptocurrency - Experiments & Comparison")

    if "experiments_payload" not in st.session_state:
        persisted = load_experiments()
        if persisted is not None:
            st.session_state.experiments_payload = persisted

    with st.sidebar:
        with st.expander("📂 Gestor de Datos", expanded=True):
            uploaded = st.file_uploader("Cargar archivo .psodata", type=["psodata"])
            if uploaded is not None:
                try:
                    data = uploaded.read()
                    imported = import_payload_from_bytes(data)
                    st.session_state.experiments_payload = imported
                    st.session_state.read_only_mode = True
                    st.success("Datos cargados en Modo Análisis (lectura).")
                except Exception as e:
                    st.error(f"Error cargando archivo: {e}")

        st.header("⚙️ Configuration")
        read_only = st.session_state.get("read_only_mode", False)
        with st.form("config_form"):
            assets_default = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]
            assets = st.multiselect(
                "Assets",
                options=assets_default,
                default=assets_default,
                disabled=read_only,
            )

            st.subheader("Market data")
            start_date = st.date_input("Start date", value=pd.to_datetime("2020-01-01"), disabled=read_only)
            end_date = st.date_input("End date", value=pd.to_datetime("2024-01-01"), disabled=read_only)
            interval = st.selectbox("Interval", options=["1d", "1wk", "1mo"], index=0, disabled=read_only)

            st.subheader("PSO")
            num_points = st.slider("Frontier points", 10, 100, 30, disabled=read_only)
            n_swarm = st.slider("Swarm size", 20, 200, 100, disabled=read_only)
            epsilon = st.number_input("Convergence epsilon", value=1e-5, format="%e", disabled=read_only)
            random_seed_enabled = st.checkbox("Use reproducible seeds", value=True, disabled=read_only)
            base_seed = st.number_input(
                "Base seed",
                min_value=0,
                max_value=10_000_000,
                value=42,
                step=1,
                disabled=(read_only or not random_seed_enabled),
            )

            st.subheader("Objectives")
            selected_objectives = st.multiselect(
                "Fitness functions",
                options=OBJECTIVE_OPTIONS,
                default=["CVaR"],
                disabled=read_only,
            )
            alpha = st.slider("CVaR alpha", 0.80, 0.99, 0.95, disabled=read_only)
            penalty = st.number_input(
                "Target penalty",
                min_value=1.0,
                max_value=5000.0,
                value=500.0,
                step=1.0,
                disabled=read_only,
            )

            st.subheader("Velocity models")
            selected_velocities = st.multiselect(
                "Velocity",
                options=VELOCITY_OPTIONS,
                default=["Inertia"],
                disabled=read_only,
            )
            c1 = st.slider("c1", 0.5, 3.0, 1.7, disabled=read_only)
            c2 = st.slider("c2", 0.5, 3.0, 1.7, disabled=read_only)
            inertia = st.slider("inertia (w)", 0.4, 1.0, 0.8, disabled=read_only)

            st.subheader("Topologies")
            selected_topologies = st.multiselect(
                "Topology",
                options=TOPOLOGY_OPTIONS,
                default=["Ring"],
                disabled=read_only,
            )
            if not read_only:
                submitted = st.form_submit_button("▶️ Run experiments", use_container_width=True)
            else:
                st.info("Modo Análisis activo. Recarga la página para realizar nuevas simulaciones.")
                submitted = False

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

        try:
            psodata = export_payload_to_bytes(st.session_state.experiments_payload)
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pso_experiments_{now}.psodata"
            st.download_button(
                "📥 Exportar Resultados (Formato .psodata)",
                data=psodata,
                file_name=filename,
                mime="application/octet-stream",
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"Error exporting results: {e}")
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
    risk_column, risk_label, _ = risk_options[selected_risk]

    experiment_names = [experiment.config.name for experiment in experiments]

    st.divider()
    tab_comparison, tab_analysis = st.tabs(["📊 Comparison", "🔎 Individual Analysis"])

    with tab_comparison:
        render_comparison_tab(
            experiments=experiments,
            metrics_by_config=metrics_by_config,
            risk_column=risk_column,
            risk_label=risk_label,
        )

    with tab_analysis:
        render_analysis_tab(
            payload=payload,
            experiments=experiments,
            metrics_by_config=metrics_by_config,
            experiment_names=experiment_names,
            assets=assets,
            risk_column=risk_column,
            risk_label=risk_label,
        )


if __name__ == "__main__":
    main()
