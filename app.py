import pandas as pd
import streamlit as st
from datetime import datetime

from src.models.fitness_function import CVaR
from src.models.topology import RingTopology
from src.models.velocity_model import Inertia
from src.run_pso import PSOInputData, run_pso
from src.ui.charts import (
    build_backtesting_returns_figure,
    build_frontier_figure,
    build_portfolio_pie_figure,
)
from src.ui.colors import get_crypto_colors
from src.ui.metrics import (
    annualized_return,
    build_metrics_dataframe,
    build_weights_table,
    top_sharpe_indices,
)
from src.utils import load_crypto_returns


def main():
    st.set_page_config(page_title="PSO Crypto", layout="wide")
    st.title("🚀 PSO Cryptocurrency - Frontera Eficiente")

    # Sidebar con configuración
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Activos
        assets_default = ["BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD"]
        assets = st.multiselect(
            "Selecciona activos",
            options=assets_default,
            default=assets_default,
        )

        # Parámetros PSO
        st.subheader("PSO Parameters")
        num_points = st.slider("Puntos en frontera", 10, 100, 30)
        n_swarm = st.slider("Tamaño del swarm", 20, 200, 100)

        st.subheader("Market Data")
        start_date = st.date_input(
            "Fecha de inicio", value=pd.to_datetime("2020-01-01")
        )
        end_date = st.date_input("Fecha de fin", value=pd.to_datetime("2024-01-01"))
        interval = st.selectbox("Intervalo", options=["1d", "1wk", "1mo"], index=0)

        st.subheader("Velocity Model (Inertia)")
        c1 = st.slider("C1 (cognitivo)", 0.5, 2.5, 1.7)
        c2 = st.slider("C2 (social)", 0.5, 2.5, 1.7)
        inertia = st.slider("Inercia (w)", 0.4, 1.0, 0.8)

        st.subheader("CVaR Parameters")
        alpha = st.slider("Alpha (confianza)", 0.80, 0.99, 0.95)
        penalty = st.number_input(
            "Penalty (target constraint)",
            min_value=500.0,
            max_value=2000.0,
            value=500.0,
            step=1.0,
            help="Cuánto penalizar si el portafolio se aleja del target. Valores típicos: 10-100"
        )

    # Botón para ejecutar
    if st.button("▶️ Ejecutar PSO", width='stretch'):
        if not assets:
            st.error("Selecciona al menos un activo.")
            return
        if start_date >= end_date:
            st.error("La fecha de inicio debe ser menor a la fecha de fin.")
            return

        # Limpiar datos de backtesting anterior para evitar incompatibilidades
        if "bt_returns_matrix" in st.session_state:
            del st.session_state.bt_returns_matrix
        if "bt_returns_index" in st.session_state:
            del st.session_state.bt_returns_index

        with st.spinner("Ejecutando PSO..."):
            try:
                # Crear dependencias
                fitness_fn = CVaR(alpha=alpha, penalty=penalty)
                velocity_model = Inertia(c1=c1, c2=c2, inertia=inertia)
                topology = RingTopology(k_neighbors=1)

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

                # Ejecutar PSO
                result = run_pso(
                    input_data=input_data,
                    num_points=num_points,
                    n_swarm=n_swarm,
                    fitness_function=fitness_fn,
                    velocity_model=velocity_model,
                    topology=topology,
                )

                # Guardar en session_state para usar después
                st.session_state.result = result
                st.session_state.assets = assets
                st.session_state.start_date = start_date.isoformat()
                st.session_state.end_date = end_date.isoformat()
                st.session_state.interval = interval
                st.session_state.alpha = alpha
                st.session_state.returns_matrix = returns_matrix
                st.session_state.returns_index = returns_index
                
                # Cargar automáticamente datos de backtesting
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
                        st.session_state.bt_returns_matrix = bt_returns_matrix
                        st.session_state.bt_returns_index = bt_returns_index
                except Exception as e:
                    st.warning(f"No se cargaron datos automáticos de backtesting: {str(e)}")
                
                st.success("✅ PSO completado!")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    # Mostrar resultados si existen
    if "result" in st.session_state:
        result = st.session_state.result
        assets = st.session_state.assets
        alpha = st.session_state.alpha
        returns_matrix = st.session_state.returns_matrix
        returns_index = st.session_state.returns_index

        st.divider()
        st.header("📊 Resultados")

        df_metrics = build_metrics_dataframe(
            returns_matrix=returns_matrix,
            weights_list=result.weights,
            cvar_alpha=alpha,
        )

        # TABS: Una para la frontera, otra para backtesting
        tab1, tab2 = st.tabs(["📈 Frontera Eficiente", "📉 Backtesting"])
        
        with tab1:
            # Gráfica: Frontera Eficiente
            col1, col2 = st.columns(2)

            with col1:
                fig_frontier = build_frontier_figure(df_metrics, alpha=alpha)
                st.plotly_chart(fig_frontier, width='stretch')

            with col2:
                st.metric("Puntos en frontera", len(result.weights))
                st.metric("Activos", len(assets))
                st.dataframe(df_metrics, width='stretch')

            # Tabla completa de métricas
            st.subheader("📊 Métricas detalladas")
            df_display = pd.DataFrame(
                {
                    f"CVaR {alpha*100:.0}%": df_metrics["cvar"] * 100,
                    "Retorno (%)": df_metrics["mean_return"] * 100,
                    "Volatilidad (%)": df_metrics["volatility"] * 100,
                    "Sharpe Ratio": df_metrics["sharpe_ratio"],
                }
            )
            st.dataframe(df_display, width='stretch')

        with tab2:
            st.subheader("🔍 Backtesting en rango diferente")
            st.info("⚠️ Usa los MISMOS activos que en el entrenamiento", icon="ℹ️")
            
            col_bt1, col_bt2 = st.columns(2)
            
            with col_bt1:
                backtest_start = st.date_input(
                    "Fecha inicio backtesting",
                    value=pd.to_datetime(st.session_state.end_date).date(),
                    key="bt_start"
                )
            
            with col_bt2:
                backtest_end = st.date_input(
                    "Fecha fin backtesting",
                    value=datetime.now().date(),
                    key="bt_end"
                )
            
            if st.button("▶️ Ejecutar Backtesting", width='stretch', key="bt_button"):
                if backtest_start >= backtest_end:
                    st.error("Fecha de inicio debe ser menor a fecha de fin")
                else:
                    with st.spinner("Cargando datos de backtesting..."):
                        try:
                            _, bt_returns_matrix, bt_returns_index = load_crypto_returns(
                                assets,
                                start=backtest_start.isoformat(),
                                end=backtest_end.isoformat(),
                                interval=st.session_state.interval,
                            )
                            
                            st.session_state.bt_returns_matrix = bt_returns_matrix
                            st.session_state.bt_returns_index = bt_returns_index
                            st.success("✅ Datos de backtesting cargados!")
                            
                        except Exception as e:
                            st.error(f"Error al cargar datos: {str(e)}")
            
            # Mostrar resultados de backtesting si existen
            if "bt_returns_matrix" in st.session_state:
                bt_returns_matrix = st.session_state.bt_returns_matrix
                bt_returns_index = st.session_state.bt_returns_index
                
                st.subheader("📉 Rendimiento acumulado en backtesting")
                default_count = min(3, len(result.weights))
                default_selected_indices = top_sharpe_indices(df_metrics, default_count)
                selected_indices = st.multiselect(
                    "Selecciona portafolios para backtesting",
                    options=list(range(len(result.weights))),
                    default=default_selected_indices,
                    format_func=lambda idx: (
                        f"Portafolio {idx + 1} | "
                        f"ret={df_metrics.iloc[idx]['mean_return']:.4f}, "
                        f"cvar={df_metrics.iloc[idx]['cvar']:.4f}"
                    ),
                    key="bt_multiselect"
                )

                if selected_indices:
                    # Obtener colores dinámicos para los activos seleccionados
                    crypto_colors = get_crypto_colors(assets)
                    
                    # Mostrar leyenda de colores UNA SOLA VEZ
                    st.subheader("📊 Leyenda de Criptos")
                    cols_legend = st.columns(len(assets))
                    for col_idx, asset in enumerate(assets):
                        with cols_legend[col_idx]:
                            color = crypto_colors[asset]
                            st.markdown(
                                f"<div style='background-color:{color}; padding:10px; border-radius:5px; text-align:center'>"
                                f"<b style='color:white'>{asset}</b></div>",
                                unsafe_allow_html=True
                            )
                    
                    st.divider()
                    
                    # Gráficas de composición con colores fijos - LAYOUT DE 2 COLUMNAS
                    st.subheader("📈 Composición de Portafolios")
                    cols_pie = st.columns(2)
                    for col_idx, idx in enumerate(selected_indices):
                        with cols_pie[col_idx % 2]:
                            # Mapear colores dinámicos a cada activo
                            colors = [crypto_colors[asset] for asset in assets]

                            fig_pie = build_portfolio_pie_figure(
                                assets=assets,
                                weights=result.weights[idx],
                                colors=colors,
                                portfolio_number=idx + 1,
                            )
                            st.plotly_chart(fig_pie, use_container_width=True)
                            
                            # Mostrar retorno esperado (diario y anual)
                            ret_daily = df_metrics.iloc[idx]['mean_return']
                            ret_annual = annualized_return(ret_daily)
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Retorno Diario", f"{ret_daily*100:.3f}%")
                            with col_b:
                                st.metric("Retorno Anual", f"{ret_annual*100:.2f}%")
                    
                    st.divider()
                    
                    # Tabla de pesos
                    st.subheader("📊 Pesos Exactos por Portafolio")
                    df_weights = build_weights_table(
                        assets=assets,
                        weights=result.weights,
                        selected_indices=selected_indices,
                    )
                    st.dataframe(
                        (df_weights * 100).round(2).astype(str) + "%",
                        width='stretch'
                    )
                    
                    # Gráfica de desempeño
                    st.subheader("📈 Rendimiento Acumulado en Backtesting")
                    fig_performance = build_backtesting_returns_figure(
                        returns_matrix=bt_returns_matrix,
                        returns_index=bt_returns_index,
                        weights=result.weights,
                        selected_indices=selected_indices,
                    )
                    st.plotly_chart(fig_performance, width='stretch')



if __name__ == "__main__":
    main()
