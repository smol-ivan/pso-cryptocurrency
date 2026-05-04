import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime


from models.fitness_function import CVaR
from models.topology import RingTopology
from models.velocity_model import Inertia
from run_pso import run_pso, PSOInputData
from utils import load_crypto_returns


def calculate_metrics(returns_matrix, weights, cvar_alpha=0.95):
    """Calcula métricas para un portafolio dado"""
    portfolio_returns = returns_matrix @ weights

    mean_ret = portfolio_returns.mean()
    volatility = portfolio_returns.std()
    var_threshold = np.percentile(portfolio_returns, (1 - cvar_alpha) * 100)
    tail_losses = portfolio_returns[portfolio_returns <= var_threshold]
    cvar = -tail_losses.mean()

    sharpe = mean_ret / volatility if volatility > 0 else 0

    return {
        "mean_return": mean_ret,
        "cvar": cvar,
        "volatility": volatility,
        "sharpe_ratio": sharpe,
    }


def plot_backtest(returns_matrix, weights_list):
    """Grafica el desempeño acumulado de los portafolios"""
    fig = go.Figure()
    
    for idx, weights in enumerate(weights_list):
        portfolio_rets = returns_matrix @ weights
        cumulative_rets = (1 + portfolio_rets).cumprod() - 1
        
        fig.add_trace(go.Scatter(
            x=np.arange(len(cumulative_rets)),
            y=cumulative_rets * 100,
            mode="lines",
            name=f"Portfolio {idx+1}",
            hovertemplate="Día %{x}<br>Retorno Acum: %{y:.2f}%<extra></extra>"
        ))
    
    fig.update_layout(
        title="Backtesting: Retorno Acumulado de Portafolios",
        xaxis_title="Días",
        yaxis_title="Retorno Acumulado (%)",
        hovermode="x unified",
        height=400
    )
    
    return fig


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
        iterations = st.slider("Iteraciones", 50, 500, 200)

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
                fitness_fn = CVaR(alpha=alpha, penalty=1e6)
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
                    iterations=iterations,
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

        # Calcular métricas para cada punto
        metrics_list = []
        for weights in result.weights:
            metrics = calculate_metrics(returns_matrix, weights, cvar_alpha=alpha)
            metrics_list.append(metrics)

        df_metrics = pd.DataFrame(metrics_list)

        # TABS: Una para la frontera, otra para backtesting
        tab1, tab2 = st.tabs(["📈 Frontera Eficiente", "📉 Backtesting"])
        
        with tab1:
            # Gráfica: Frontera Eficiente
            col1, col2 = st.columns(2)

            with col1:
                fig_frontier = go.Figure()
                fig_frontier.add_trace(
                    go.Scatter(
                        x=df_metrics["cvar"],
                        y=df_metrics["mean_return"],
                        mode="markers+lines",
                        name="Frontera Eficiente",
                        marker=dict(
                            size=8,
                            color=df_metrics["sharpe_ratio"],
                            colorscale="Viridis",
                            showscale=True,
                        ),
                    )
                )
                fig_frontier.update_layout(
                    title="Frontera Eficiente (Risk vs Return)",
                    xaxis_title=f"CVaR {alpha * 100}%",
                    yaxis_title="Retorno Esperado",
                    hovermode="closest",
                )
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
                    value=st.session_state.end_date,
                    key="bt_start"
                )
            
            with col_bt2:
                backtest_end = st.date_input(
                    "Fecha fin backtesting",
                    value=datetime.now(),
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
                top_sharpe_indices = (
                    df_metrics["sharpe_ratio"].nlargest(default_count).index.to_list()
                    if default_count > 0
                    else []
                )
                selected_indices = st.multiselect(
                    "Selecciona portafolios para backtesting",
                    options=list(range(len(result.weights))),
                    default=top_sharpe_indices,
                    format_func=lambda idx: (
                        f"Portafolio {idx + 1} | "
                        f"ret={df_metrics.iloc[idx]['mean_return']:.4f}, "
                        f"cvar={df_metrics.iloc[idx]['cvar']:.4f}"
                    ),
                    key="bt_multiselect"
                )

                if selected_indices:
                    # Gráficas de composición
                    cols_comp = st.columns(len(selected_indices))
                    for col_idx, idx in enumerate(selected_indices):
                        with cols_comp[col_idx]:
                            fig_pie = go.Figure(data=[go.Pie(
                                labels=assets,
                                values=result.weights[idx],
                                title=f"Portafolio {idx + 1}<br>Ret: {df_metrics.iloc[idx]['mean_return']*100:.2f}%"
                            )])
                            fig_pie.update_layout(height=400)
                            st.plotly_chart(fig_pie, use_container_width=True)
                    
                    # Tabla de pesos
                    st.subheader("📊 Composición de Portafolios (Pesos)")
                    weights_data = {}
                    for col_idx, idx in enumerate(selected_indices):
                        weights_data[f"Portafolio {idx + 1}"] = result.weights[idx]
                    df_weights = pd.DataFrame(weights_data, index=assets)
                    st.dataframe(
                        (df_weights * 100).round(2).astype(str) + "%",
                        use_container_width=True
                    )
                    
                    # Gráfica de desempeño
                    st.subheader("📈 Rendimiento Acumulado en Backtesting")
                    fig_performance = go.Figure()
                    for idx in selected_indices:
                        portfolio_returns = bt_returns_matrix @ result.weights[idx]
                        cumulative_returns = np.cumprod(1 + portfolio_returns) - 1
                        fig_performance.add_trace(
                            go.Scatter(
                                x=bt_returns_index,
                                y=cumulative_returns * 100,
                                mode="lines",
                                name=f"Portafolio {idx + 1}",
                                hovertemplate="Fecha: %{x|%Y-%m-%d}<br>Retorno: %{y:.2f}%<extra></extra>"
                            )
                        )

                    fig_performance.update_layout(
                        title="Rendimiento en Backtesting (Retorno Acumulado %)",
                        xaxis_title="Fecha",
                        yaxis_title="Retorno Acumulado (%)",
                        hovermode="x unified",
                        height=500,
                    )
                    st.plotly_chart(fig_performance, width='stretch')



if __name__ == "__main__":
    main()
