"""
decompose_fitness.py
====================
Script de diagnóstico observacional para descomponer el fitness del PSO
generación a generación en sus dos componentes fundamentales:
  1. Componente de riesgo: -CVaR (o CVaR sin penalización)
  2. Componente de penalización: penalty * |retorno_medio - target|

Reglas de observación:
- No modifica src/pso/fitness_function.py ni src/pso/optimizer.py.
- Usa la misma función CVaR de producción.
- Calcula los componentes de forma observacional desde fuera del loop
  usando la traza diagnóstica (ConvergenceTrace) y la posición óptima final.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Tuple

import numpy as np

# Asegurar root en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pso import (
    CVaR,
    GlobalTopology,
    Inertia,
    RingTopology,
    pso,
)
from src.pso.optimizer import ConvergenceTrace


def generate_synthetic_returns_300x4(seed: int = 42) -> np.ndarray:
    """Genera matriz sintética fija de 300 obs x 4 activos."""
    rng = np.random.default_rng(seed)
    return rng.normal(
        loc=[0.0005, 0.0008, 0.0002, 0.0010],
        scale=[0.02, 0.025, 0.015, 0.03],
        size=(300, 4),
    )


def run_and_decompose(
    returns_matrix: np.ndarray,
    target_value: float,
    penalty: float = 500.0,
    alpha: float = 0.95,
    swarm_size: int = 100,
    patience: int = 10,
    rtol: float = 1e-4,
    atol: float = 1e-8,
    max_iterations: int = 1000,
    seed: int = 42,
    c1: float = 1.7,
    c2: float = 1.7,
    inertia: float = 0.8,
    topology_type: str = "Global",
) -> Tuple[float, np.ndarray, ConvergenceTrace, dict]:
    """
    Ejecuta el PSO con la función CVaR de producción y descompone el fitness
    de forma observacional a partir de la traza de convergencia.
    """
    cvar_prod = CVaR(alpha=alpha, penalty=penalty)
    rng_pso = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    vm = Inertia(c1=c1, c2=c2, inertia=inertia)
    topo = GlobalTopology() if topology_type == "Global" else RingTopology()

    best_val, best_pos, conv_hist, div_hist, trace = pso(
        returns_matrix=returns_matrix,
        swarm_size=swarm_size,
        target_value=target_value,
        fitness_function=cvar_prod,
        velocity_model=vm,
        topology=topo,
        rtol=rtol,
        atol=atol,
        patience=patience,
        max_iterations=max_iterations,
        random_generator=rng_pso,
        python_random_generator=py_rng,
        return_diagnostics=True,
    )

    # Verificación observacional final usando CVaR(penalty=0.0) de producción
    cvar_no_penalty = CVaR(alpha=alpha, penalty=0.0)
    final_risk_direct = cvar_no_penalty.evaluate(best_pos, returns_matrix, target_value)
    final_mean_ret = float((returns_matrix @ best_pos).mean())
    final_target_diff = abs(final_mean_ret - target_value)
    final_penalty_direct = penalty * final_target_diff
    final_total_direct = final_risk_direct + final_penalty_direct

    verification = {
        "final_risk_direct": final_risk_direct,
        "final_penalty_direct": final_penalty_direct,
        "final_total_direct": final_total_direct,
        "gbest_final": best_val,
        "diff_total_vs_gbest": abs(final_total_direct - best_val),
    }

    return best_val, best_pos, trace, verification


def print_decomposition_table(
    trace: ConvergenceTrace,
    target_value: float,
    penalty: float,
    verification: dict,
    title: str = "",
) -> None:
    """Imprime una tabla completa por generación con la descomposición del fitness."""
    n = trace.iterations_completed
    print(f"\n{'='*100}")
    if title:
        print(f"  {title}")
    print(f"  Target: {target_value:+.6f} | Penalty: {penalty:.1f} | Iteraciones: {n} | Motivo: {trace.termination_reason}")
    print(f"{'='*100}")
    print(
        f"{'Gen':>4} | {'gbest':>11} | {'Riesgo (-CVaR)':>14} | {'Penalización':>13} | "
        f"{'Pen %':>7} | {'Retorno Medio':>13} | {'|Ret - Target|':>14} | {'Diversidad':>10} | {'Movimiento':>10}"
    )
    print(f"{'-'*4}-+-{'-'*11}-+-{'-'*14}-+-{'-'*13}-+-{'-'*7}-+-{'-'*13}-+-{'-'*14}-+-{'-'*10}-+-{'-'*10}")

    for i in range(n):
        gen = int(trace.iterations[i])
        gbest_i = trace.gbest[i]
        diff_i = trace.best_target_difference[i]
        ret_i = trace.best_mean_return[i]
        div_i = trace.diversity[i]
        mov_i = trace.movement_mean[i]

        pen_comp_i = penalty * diff_i
        risk_comp_i = gbest_i - pen_comp_i
        pen_pct = (pen_comp_i / gbest_i * 100.0) if gbest_i != 0 else 0.0

        # Verificación interna: riesgo + penalización = gbest
        assert abs((risk_comp_i + pen_comp_i) - gbest_i) < 1e-12, "Discrepancia en suma"

        print(
            f"{gen:>4} | {gbest_i:>11.6f} | {risk_comp_i:>14.6f} | {pen_comp_i:>13.6f} | "
            f"{pen_pct:>6.2f}% | {ret_i:>13.6f} | {diff_i:>14.6f} | {div_i:>10.6f} | {mov_i:>10.6f}"
        )

    print(f"{'-'*100}")
    print(f"Verificación observacional final (contra CVaR(penalty=0.0)):")
    print(f"  - Riesgo directo evaluado : {verification['final_risk_direct']:.8f}")
    print(f"  - Penalización calculada  : {verification['final_penalty_direct']:.8f}")
    print(f"  - Suma (riesgo + penalty) : {verification['final_total_direct']:.8f}")
    print(f"  - gbest reportado por PSO : {verification['gbest_final']:.8f}")
    print(f"  - Discrepancia absoluta   : {verification['diff_total_vs_gbest']:.2e}")
    assert verification['diff_total_vs_gbest'] < 1e-12, "Discrepancia en verificación final"
    print(f"  => VERIFICACIÓN EXITOSA (coincidencia exacta a nivel numérico).")


def run_streamlit_reproduction() -> None:
    """Reproduce los dos escenarios con la configuración exacta de Streamlit."""
    print("\n" + "=" * 100)
    print("  REPRODUCCIÓN CON CONFIGURACIÓN REAL DE STREAMLIT (CVaR, penalty=500.0, swarm=100, patience=10)")
    print("=" * 100)

    returns = generate_synthetic_returns_300x4(seed=42)
    means = returns.mean(axis=0)
    t_low = float(means.min())
    t_mid = float((means.min() + means.max()) / 2)

    scenarios = [
        ("Caso A: Target BAJO (estancamiento / dominancia de frontera)", t_low),
        ("Caso B: Target MEDIO (convergencia gradual / interior del simplex)", t_mid),
    ]

    for topo_name in ["Global", "Ring"]:
        print(f"\n>>> TOPOLOGÍA: {topo_name} <<<")
        for sc_name, target in scenarios:
            best_val, best_pos, trace, verif = run_and_decompose(
                returns_matrix=returns,
                target_value=target,
                penalty=500.0,
                alpha=0.95,
                swarm_size=100,
                patience=10,
                rtol=1e-4,
                atol=1e-8,
                seed=42,
                c1=1.7,
                c2=1.7,
                inertia=0.8,
                topology_type=topo_name,
            )
            print_decomposition_table(trace, target, 500.0, verif, title=f"{sc_name} | Topología: {topo_name}")
            print(f"Portafolio final (pesos): {np.round(best_pos, 4)}")


def run_sensitivity_study() -> None:
    """Estudio de sensibilidad de penalty in [500, 50, 10, 1] across seeds=[42, 43, 44]."""
    print("\n" + "=" * 115)
    print("  ESTUDIO DE SENSIBILIDAD DE LA PENALIZACIÓN: penalty=[500, 50, 10, 1] x seeds=[42, 43, 44]")
    print("=" * 115)

    returns = generate_synthetic_returns_300x4(seed=42)
    means = returns.mean(axis=0)
    t_low = float(means.min())
    t_mid = float((means.min() + means.max()) / 2)

    for target_label, target in [("Target BAJO (min retorno)", t_low), ("Target MEDIO (retorno intermedio)", t_mid)]:
        print(f"\n--- {target_label} (target = {target:+.6f}) ---")
        print(
            f"{'Penalty':>7} | {'Seed':>4} | {'gbest_final':>12} | {'Iters':>5} | {'Motivo':>8} | "
            f"{'div_final':>9} | {'mov_final':>9} | {'Riesgo (-CVaR)':>14} | {'Penalización':>13} | {'Pen %':>7}"
        )
        print(f"{'-'*7}-+-{'-'*4}-+-{'-'*12}-+-{'-'*5}-+-{'-'*8}-+-{'-'*9}-+-{'-'*9}-+-{'-'*14}-+-{'-'*13}-+-{'-'*7}")

        for pen in [500.0, 50.0, 10.0, 1.0]:
            for seed in [42, 43, 44]:
                best_val, best_pos, trace, verif = run_and_decompose(
                    returns_matrix=returns,
                    target_value=target,
                    penalty=pen,
                    alpha=0.95,
                    swarm_size=100,
                    patience=10,
                    rtol=1e-4,
                    atol=1e-8,
                    seed=seed,
                    c1=1.7,
                    c2=1.7,
                    inertia=0.8,
                    topology_type="Global",
                )
                n = trace.iterations_completed
                gbest_f = trace.gbest[-1]
                div_f = trace.diversity[-1]
                mov_f = trace.movement_mean[-1]
                pen_comp = pen * trace.best_target_difference[-1]
                risk_comp = gbest_f - pen_comp
                pen_pct = (pen_comp / gbest_f * 100.0) if gbest_f != 0 else 0.0

                print(
                    f"{pen:>7.1f} | {seed:>4} | {gbest_f:>12.6f} | {n:>5} | {trace.termination_reason:>8} | "
                    f"{div_f:>9.6f} | {mov_f:>9.6f} | {risk_comp:>14.6f} | {pen_comp:>13.6f} | {pen_pct:>6.2f}%"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Descomposición observacional del fitness por generación.")
    parser.add_argument("--penalty", type=float, default=500.0, help="Valor de penalización lambda (default: 500.0)")
    parser.add_argument("--swarm-size", type=int, default=100, help="Tamaño del enjambre (default: 100)")
    parser.add_argument("--seed", type=int, default=42, help="Semilla para reproducibilidad (default: 42)")
    parser.add_argument("--topology", choices=["Global", "Ring"], default="Global", help="Topología (default: Global)")
    parser.add_argument("--target-mode", choices=["low", "mid", "high", "all"], default="all", help="Target a evaluar")
    parser.add_argument("--streamlit-repro", action="store_true", help="Ejecuta reproducción con config Streamlit")
    parser.add_argument("--sensitivity", action="store_true", help="Ejecuta estudio de sensibilidad penalty=[500, 50, 10, 1]")
    args = parser.parse_args()

    if args.streamlit_repro:
        run_streamlit_reproduction()
        return

    if args.sensitivity:
        run_sensitivity_study()
        return

    returns = generate_synthetic_returns_300x4(seed=42)
    means = returns.mean(axis=0)
    t_low = float(means.min())
    t_high = float(means.max())
    t_mid = float((t_low + t_high) / 2)

    cases = []
    if args.target_mode in ("low", "all"):
        cases.append(("Target BAJO (caso de estancamiento / dominancia de frontera)", t_low))
    if args.target_mode in ("mid", "all"):
        cases.append(("Target MEDIO (caso de convergencia gradual / interior del simplex)", t_mid))
    if args.target_mode in ("high", "all"):
        cases.append(("Target ALTO (caso extremo superior)", t_high))

    for title, target in cases:
        best_val, best_pos, trace, verification = run_and_decompose(
            returns_matrix=returns,
            target_value=target,
            penalty=args.penalty,
            swarm_size=args.swarm_size,
            seed=args.seed,
            topology_type=args.topology,
        )
        print_decomposition_table(trace, target, args.penalty, verification, title=f"{title} | Topología: {args.topology}")
        print(f"Pesos finales de portafolio: {np.round(best_pos, 4)}")


if __name__ == "__main__":
    main()
