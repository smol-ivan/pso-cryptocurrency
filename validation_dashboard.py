"""Independent, read-only Streamlit validation dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from validation_dashboard_logic import run_validation_suite


def _render_status(label: str, passed: bool) -> None:
    (st.success if passed else st.error)(f"{label}: {'Aprobado' if passed else 'Fallido'}")


def _render_table(rows: list[dict], columns: list[str]) -> None:
    frame = pd.DataFrame(rows)
    st.dataframe(frame[columns], use_container_width=True, hide_index=True)


def _execute_validation() -> bool:
    st.session_state["validation_results"] = None
    try:
        st.session_state["validation_results"] = run_validation_suite()
    except Exception as error:
        st.error(f"No se pudo completar la validación: {error}")
        return False
    return True


def _render_convergence(results: dict) -> None:
    figure = go.Figure()
    for name, runs in results["runs"].items():
        for result in runs:
            figure.add_trace(
                go.Scatter(
                    x=result["iterations"],
                    y=result["gbest"],
                    mode="lines",
                    name=f"{name} (semilla {result['seed']})",
                )
            )
    figure.update_layout(
        title="Mejor fitness global por iteración",
        xaxis_title="Iteración registrada (posterior al movimiento)",
        yaxis_title="Fitness gbest (menor es mejor)",
        legend_title="Topología",
    )
    st.plotly_chart(figure, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="PSO · Validación independiente", layout="wide")
    st.title("Validación independiente del PSO")
    st.write(
        "Esta página ejecuta únicamente casos sintéticos predefinidos del "
        "optimizador. No descarga datos, no carga `.psodata` y no modifica "
        "resultados persistidos."
    )
    st.info(
        "Los parámetros y semillas son fijos en el código. Los resultados "
        "sirven para validar propiedades concretas del optimizador, no para "
        "demostrar superioridad financiera ni validar un backtesting."
    )
    with st.expander("Casos incluidos", expanded=True):
        st.markdown(
            "- Factibilidad long-only y suma de pesos.\n"
            "- Sphere sobre el simplex con óptimo uniforme conocido.\n"
            "- Mínima varianza long-only contra una referencia independiente.\n"
            "- Caso manual de VaR/CVaR y penalización.\n"
            "- Convergencia Ring/Global con diagnósticos disponibles.\n"
            "- Reproducibilidad con la misma configuración y semilla."
        )
    st.caption(
        "Configuración fija: 30 partículas, Inertia (c1=1.7, c2=1.7, w=0.8), "
        "rtol=1e-4, atol=1e-8, paciencia=10. Semillas: 11–15, "
        "101–103 emparejadas para Ring/Global y 777."
    )

    if "validation_results" not in st.session_state:
        st.info("Aún no hay resultados. Pulsa «Ejecutar validación».")
    if st.button("Ejecutar validación", type="primary"):
        with st.spinner("Ejecutando casos sintéticos..."):
            executed = _execute_validation()
        if executed:
            st.success("Validación ejecutada; los resultados quedan en memoria durante esta sesión.")
    if st.session_state.get("validation_results") is None:
        return

    results = st.session_state.validation_results
    if st.button("Repetir validación", type="secondary"):
        with st.spinner("Repitiendo casos sintéticos..."):
            executed = _execute_validation()
        if executed:
            st.rerun()

    st.subheader("Resumen")
    summary = results["summary"]
    columns = st.columns(4)
    columns[0].metric("Casos evaluados", summary["cases"])
    columns[1].metric("Aprobados", summary["passed"])
    columns[2].metric("Fallidos", summary["cases"] - summary["passed"])
    columns[3].metric("Tiempo", f"{results['elapsed_seconds']:.2f} s")

    tabs = st.tabs(
        ["Factibilidad", "Referencias", "VaR/CVaR", "Convergencia", "Reproducibilidad"]
    )
    with tabs[0]:
        _render_status("Factibilidad", results["feasibility"]["ok"])
        feasibility = results["feasibility"]
        st.write(
            {
                "Todos los pesos finitos": feasibility["all_finite"],
                "Pesos no negativos": feasibility["nonnegative"],
                "Suma aproximadamente 1": feasibility["sums_ok"],
            }
        )
        st.dataframe(
            pd.DataFrame(
                {
                    "Activo sintético": ["A", "B", "C", "D"],
                    "Peso obtenido": feasibility["weights"],
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    with tabs[1]:
        st.markdown("**Sphere sobre el simplex**")
        _render_status("Criterios Sphere", results["sphere"]["ok"])
        _render_table(
            results["sphere"]["rows"],
            ["seed", "fitness", "distance", "iterations", "termination"],
        )
        st.write("Óptimo de referencia:", results["sphere"]["optimum"])
        st.markdown("**Mínima varianza long-only**")
        _render_status("Criterios de mínima varianza", results["minimum_variance"]["ok"])
        _render_table(
            [
                {key: value for key, value in row.items() if key != "weights"}
                for row in results["minimum_variance"]["rows"]
            ],
            ["seed", "fitness", "relative_gap", "iterations", "termination"],
        )
        st.write(
            "Referencia independiente:",
            results["minimum_variance"]["reference_weights"],
            f"f* = {results['minimum_variance']['reference_value']:.15f}",
        )
        st.caption(
            "Este benchmark es mínima varianza sintética; no valida la función "
            "CVaR penalizada ni una estrategia financiera."
        )
    with tabs[2]:
        manual = results["manual_cvar"]
        _render_status("Caso manual", manual["ok"])
        st.table(
            pd.DataFrame(
                [
                    ["Riesgo CVaR esperado", manual["expected_cvar_risk"], manual["calculated_cvar_risk"]],
                    ["Fitness con target 0.15 y penalty 50", manual["expected_penalized_fitness"], manual["calculated_penalized_fitness"]],
                ],
                columns=["Métrica", "Esperado", "Calculado"],
            )
        )
        st.caption(
            "La convención observada usa la cola inferior, percentil NumPy, "
            "empates incluidos con <= y riesgo = -CVaR de retorno."
        )
    with tabs[3]:
        _render_status("Diagnósticos de convergencia", results["convergence_ok"])
        _render_convergence(results["convergence"])
        st.caption(
            "Una curva que se estabiliza temprano no se etiqueta por sí sola "
            "como defecto. La primera fila corresponde al estado posterior al "
            "primer movimiento; solo se muestran métricas disponibles. Ring y "
            "Global usan la misma semilla en cada par, lo que mejora el control "
            "experimental, pero no demuestra superioridad general de ninguna "
            "topología."
        )
        selected = st.selectbox("Topología", ["Ring", "Global"])
        selected_seed = st.selectbox(
            "Semilla emparejada", list(results["convergence"]["seeds"])
        )
        diagnostic = next(
            result
            for result in results["convergence"]["runs"][selected]
            if result["seed"] == selected_seed
        )
        _render_table(
            [
                {
                    "iteración": int(iteration),
                    "diversidad": float(diversity),
                    "movimiento medio": float(movement),
                    "reparaciones": int(repair),
                }
                for iteration, diversity, movement, repair in zip(
                    diagnostic["iterations"],
                    diagnostic["diversity"],
                    diagnostic["movement_mean"],
                    diagnostic["repairs"],
                )
            ],
            ["iteración", "diversidad", "movimiento medio", "reparaciones"],
        )
        st.write("Motivo de terminación:", diagnostic["termination"])
    with tabs[4]:
        reproducible = results["reproducibility"]
        _render_status("Misma semilla y configuración", reproducible["ok"])
        st.write(
            {
                "Fitness equivalente": reproducible["fitness_equal"],
                "Pesos idénticos": reproducible["weights_equal"],
                "Traza idéntica": reproducible["trace_equal"],
            }
        )


if __name__ == "__main__":
    main()
