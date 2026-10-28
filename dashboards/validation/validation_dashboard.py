"""Independent, read-only Streamlit validation dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboards.validation.validation_dashboard_logic import (
    MARKET_PENALTY,
    evaluate_extreme_cases,
    run_market_diagnostic,
    run_validation_suite,
)


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


def _execute_market_diagnostic() -> bool:
    st.session_state["market_diagnostic_results"] = None
    try:
        st.session_state["market_diagnostic_results"] = run_market_diagnostic()
    except Exception as error:
        st.error(f"No se pudo completar el diagnóstico de mercado: {error}")
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


def _render_market_diagnostic(results: dict) -> None:
    st.subheader("Metadatos efectivos")
    st.write(
        {
            "Activos": ", ".join(results["assets"]),
            "Período solicitado": f"{results['requested_start']} → {results['requested_end']}",
            "Período disponible": f"{results['available_start']} → {results['available_end']}",
            "Observaciones": results["observations"],
            "Intervalo": results["interval"],
            "Recuperado (UTC)": results["retrieved_at"],
            "Semillas": results["seeds"],
            "Penalización": MARKET_PENALTY,
            "Target mínimo": results["target_values"]["minimum"],
            "Target intermedio": results["target_values"]["intermediate"],
        }
    )
    st.caption(
        "Se ejecutan dos targets sobre la misma matriz: el mínimo de las medias "
        "por activo y un punto intermedio entre la media mínima y máxima. La "
        "aplicación principal usa 30 puntos de frontera; estos dos puntos se "
        "seleccionan para contrastar un extremo y un caso intermedio. Los "
        "retornos son logarítmicos por observación."
    )

    target_name = st.selectbox(
        "Objetivo de retorno",
        ["minimum", "intermediate"],
        format_func=lambda value: {
            "minimum": "Mínimo de las medias por activo",
            "intermediate": "Intermedio entre mínimo y máximo",
        }[value],
    )
    runs = results["runs"][target_name]
    selected_topology = st.selectbox("Topología de mercado", ["Ring", "Global"])
    selected_seed = st.selectbox("Semilla de mercado", list(results["seeds"]))
    run = next(item for item in runs[selected_topology] if item["seed"] == selected_seed)

    convergence = go.Figure()
    convergence.add_trace(go.Scatter(x=run["iterations"], y=run["gbest"], mode="lines"))
    convergence.update_layout(
        title="Convergencia: mejor fitness global",
        xaxis_title="Iteración registrada (posterior al movimiento)",
        yaxis_title="Fitness CVaR + penalización (menor es mejor)",
    )
    st.plotly_chart(convergence, use_container_width=True)

    population = go.Figure()
    population.add_trace(go.Scatter(x=run["iterations"], y=run["diversity"], name="Diversidad"))
    population.add_trace(go.Scatter(x=run["iterations"], y=run["movement_mean"], name="Movimiento medio"))
    population.update_layout(
        title="Diversidad y movimiento",
        xaxis_title="Iteración registrada",
        yaxis_title="Magnitud euclídea en pesos",
    )
    st.plotly_chart(population, use_container_width=True)

    gap = go.Figure()
    gap.add_trace(
        go.Scatter(
            x=run["iterations"],
            y=run["target_gap_history"],
            name="Brecha absoluta",
        )
    )
    gap.update_layout(title="Brecha al objetivo", xaxis_title="Iteración registrada")
    st.plotly_chart(gap, use_container_width=True)

    repairs = go.Figure()
    repairs.add_trace(go.Bar(x=run["iterations"], y=run["repairs"], name="Partículas reparadas"))
    repairs.update_layout(
        title="Reparaciones de posición por iteración",
        xaxis_title="Iteración registrada",
        yaxis_title="Cantidad de partículas",
    )
    st.plotly_chart(repairs, use_container_width=True)

    st.subheader("Descomposición de la mejor solución")
    st.write(
        {
            "Retorno medio por observación": run["mean_return"],
            "Objetivo": run["target"],
            "Brecha absoluta": run["target_gap"],
            "CVaR usado como riesgo": run["cvar"],
            "Penalización": run["penalty_component"],
            "Fitness total": run["fitness"],
            "Suma riesgo + penalización": run["fitness_components_sum"],
            "Peso máximo": run["max_weight"],
            "Pesos >= 0.95": run["weights_near_vertices"],
            "Iteraciones efectivas": run["iterations_completed"],
            "Criterio de terminación": run["termination"],
        }
    )
    st.dataframe(
        pd.DataFrame({"Activo": results["assets"], "Peso final": run["weights"]}),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "La traza comienza después del primer movimiento. `repairs` cuenta "
        "partículas cuya posición fue modificada por la reparación; no mide la "
        "magnitud de la corrección y no representa reparación de velocidad."
    )
    st.subheader("Casos extremos sintéticos")
    st.dataframe(pd.DataFrame(evaluate_extreme_cases()), use_container_width=True, hide_index=True)
    st.warning(
        "Estos resultados son diagnósticos: no demuestran optimalidad global ni "
        "superioridad general de Ring o Global. La magnitud de reparación no está "
        "instrumentada en el optimizador actual."
    )


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
        st.divider()
        st.header("Diagnóstico con datos reales")
        st.write(
            "Esta sección permanece inactiva hasta que pulses el botón. Descargará "
            "BTC-USD, ETH-USD, SOL-USD y ADA-USD con el cargador existente, usando "
            "2020-01-01–2024-01-01, intervalo 1d, CVaR alpha=0.95 y penalización "
            f"{MARKET_PENALTY:g}. Comparará Ring y Global con semillas fijas "
            "para un target mínimo y uno intermedio."
        )
        if st.button("Ejecutar diagnóstico con datos reales", type="primary"):
            with st.spinner("Descargando datos y ejecutando diagnóstico..."):
                _execute_market_diagnostic()
        if st.session_state.get("market_diagnostic_results") is not None:
            _render_market_diagnostic(st.session_state["market_diagnostic_results"])
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

    st.divider()
    st.header("Diagnóstico con datos reales")
    st.write(
        "La ejecución de mercado es independiente de los casos sintéticos y "
        "solo comienza mediante una acción explícita. No se escriben resultados "
        "experimentales en archivos persistentes."
    )
    if st.button("Ejecutar diagnóstico con datos reales", type="primary"):
        with st.spinner("Descargando datos y ejecutando diagnóstico..."):
            executed = _execute_market_diagnostic()
        if executed:
            st.success("Diagnóstico de mercado completado; resultados en memoria de sesión.")
    market_results = st.session_state.get("market_diagnostic_results")
    if market_results is not None:
        _render_market_diagnostic(market_results)


if __name__ == "__main__":
    main()
