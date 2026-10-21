"""
diagnose_convergence.py
=======================
Script de diagnóstico de convergencia del PSO.

Ejecuta el algoritmo con configuraciones controladas (matriz sintética y
"realista") e imprime tablas descriptivas por target y por semilla.
No modifica ningún test ni código de src/.

Uso:
    ./.venv/bin/python scripts/diagnose_convergence.py
    ./.venv/bin/python scripts/diagnose_convergence.py --scenario realistic
    ./.venv/bin/python scripts/diagnose_convergence.py --scenario all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# Asegurar que el root del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pso import (
    CVaR,
    Variance,
    Constriction,
    GlobalTopology,
    Inertia,
    RingTopology,
    pso,
)
from src.pso.optimizer import ConvergenceTrace

# ─────────────────────────────────────────────────────────────────────────────
# Matrices de retornos
# ─────────────────────────────────────────────────────────────────────────────

# Misma matriz que los tests (PSO-01 / PSO-02) — completamente controlable
RETURNS_SYNTHETIC = np.array(
    [
        [0.01,  0.02, -0.01],
        [0.02, -0.01,  0.03],
        [-0.01, 0.01,  0.02],
        [0.03,  0.00,  0.01],
    ],
    dtype=float,
)

# Matriz más grande que simula un escenario "realista":
# 200 períodos, 4 activos con retornos y correlaciones distintas.
# Semilla fija para reproducibilidad del script.
_rng = np.random.default_rng(42)
_base = _rng.normal(loc=[0.0005, 0.0008, 0.0002, 0.0010], scale=[0.02, 0.025, 0.015, 0.03], size=(200, 4))
RETURNS_REALISTIC = _base

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de formato
# ─────────────────────────────────────────────────────────────────────────────

SEP = "─" * 80
THIN = "·" * 80


def _header(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def _section(title: str) -> None:
    print(f"\n  {title}")
    print(f"  {'─' * (len(title) + 2)}")


def _flag(condition: bool, label: str) -> str:
    return f"⚠  {label}" if condition else f"   {label}"


# ─────────────────────────────────────────────────────────────────────────────
# Resumen compacto de una traza
# ─────────────────────────────────────────────────────────────────────────────

def _summarize_trace(
    trace: ConvergenceTrace,
    target: float,
    label: str = "",
    n_stages: int = 5,
) -> None:
    """Imprime un resumen detallado de una ConvergenceTrace."""
    n = trace.iterations_completed
    if n == 0:
        print(f"    {label}  ← SIN ITERACIONES")
        return

    gbest_init = trace.gbest[0]
    gbest_final = trace.gbest[-1]
    gbest_drop = gbest_init - gbest_final          # cuánto bajó (positivo = mejoró)
    gbest_drop_pct = (gbest_drop / abs(gbest_init) * 100) if gbest_init != 0 else 0.0

    div_init = trace.initial_diversity
    div_final = trace.diversity[-1]
    div_pct = (div_final / div_init * 100) if div_init > 0 else float("nan")

    mov_final = trace.movement_mean[-1]
    last_sig = int(trace.last_significant_improvement[-1])
    repairs_total = int(trace.repairs.sum())
    repairs_per_it = repairs_total / n

    term_reason = trace.termination_reason
    term_iter = trace.termination_iteration

    # Cuándo paró de mejorar de forma significativa (relativo a total)
    last_sig_display = last_sig if last_sig >= 0 else "nunca (desde iter 0)"

    # Flags de diagnóstico
    early_collapse = div_final < 1e-6 and n < 20
    stalled_with_movement = mov_final > 1e-4 and gbest_drop < 1e-6
    penalty_dominates = gbest_init > 1.0 and gbest_final < 0.1  # penalización alta al inicio
    no_improvement_after_init = last_sig <= 0

    print()
    print(f"    {'Target':12s}: {target:+.6f}   │   {label}")
    print(f"    {'Iteraciones':12s}: {n}   (terminó por: {term_reason!r} en iter {term_iter})")
    print()
    print(f"    ── gbest ──")
    print(f"       Inicial : {gbest_init:.8f}")
    print(f"       Final   : {gbest_final:.8f}")
    print(f"       Mejora  : {gbest_drop:+.8f}  ({gbest_drop_pct:.2f}%)")
    print(f"       Última mejora significativa: iter {last_sig_display}")
    print()
    print(f"    ── Diversidad (dispersión del enjambre) ──")
    print(f"       Inicial : {div_init:.6f}")
    print(f"       Final   : {div_final:.6f}  ({div_pct:.1f}% de la inicial)")
    print(f"       Máx dist final: {trace.diversity_max_distance[-1]:.6f}")
    print()
    print(f"    ── Movimiento ──")
    print(f"       Movimiento final (media): {mov_final:.6f}")
    print(f"       Movimiento final (máx)  : {trace.movement_max[-1]:.6f}")
    print()
    print(f"    ── Restricciones ──")
    print(f"       Reparaciones totales: {repairs_total}  ({repairs_per_it:.1f} / iter)")
    print(f"       Valores inválidos   : {int(trace.invalid_values.sum())}")
    print(f"       Suma pesos [min,max]: [{trace.weight_sum_min.mean():.4f}, {trace.weight_sum_max.mean():.4f}]")
    print()
    print(f"    ── Distancia al target ──")
    print(f"       Mejor retorno medio  : {trace.best_mean_return[-1]:+.6f}")
    print(f"       Diferencia al target : {trace.best_target_difference[-1]:.6f}")

    # Flags
    flags = []
    if early_collapse:
        flags.append(_flag(True, f"Colapso temprano: diversidad llegó a {div_final:.2e} en {n} iteraciones"))
    if stalled_with_movement:
        flags.append(_flag(True, f"Movimiento sin mejora: mov={mov_final:.4f} pero gbest mejoró {gbest_drop:.2e}"))
    if no_improvement_after_init:
        flags.append(_flag(True, "Sin mejora significativa después de la inicialización (iter 0)"))
    if penalty_dominates:
        flags.append(_flag(True, f"Fitness cayó mucho: {gbest_init:.4f} → {gbest_final:.4f} (¿penalización dominante?)"))

    if flags:
        print()
        print(f"    ── Flags ──")
        for f in flags:
            print(f"       {f}")

    # Progresión por etapas (N puntos distribuidos a lo largo de las iteraciones)
    _print_progression(trace, n_stages)


def _print_progression(trace: ConvergenceTrace, n_stages: int) -> None:
    """Muestra n_stages filas distribuidas uniformemente en las iteraciones."""
    n = trace.iterations_completed
    if n < 2:
        return
    indices = np.round(np.linspace(0, n - 1, min(n_stages, n))).astype(int)
    # Eliminar duplicados manteniendo orden
    seen = set()
    indices = [i for i in indices if not (i in seen or seen.add(i))]

    print()
    print(f"    ── Progresión por etapas ──")
    print(f"    {'Iter':>5}  {'gbest':>12}  {'div':>10}  {'mov_mean':>10}  {'mejora':>12}  {'rep':>5}  {'pait':>5}")
    print(f"    {'─'*5}  {'─'*12}  {'─'*10}  {'─'*10}  {'─'*12}  {'─'*5}  {'─'*5}")
    for i in indices:
        it = int(trace.iterations[i])
        gbest = trace.gbest[i]
        div = trace.diversity[i]
        mov = trace.movement_mean[i]
        imp = trace.improvement[i]
        rep = int(trace.repairs[i])
        pw = int(trace.patience_wait[i])
        print(f"    {it:>5}  {gbest:>12.8f}  {div:>10.6f}  {mov:>10.6f}  {imp:>12.2e}  {rep:>5}  {pw:>5}")


# ─────────────────────────────────────────────────────────────────────────────
# Comparar dos semillas para un mismo target
# ─────────────────────────────────────────────────────────────────────────────

def _compare_seeds(
    returns_matrix: np.ndarray,
    target: float,
    seeds: list[int],
    fitness_function,
    velocity_model_factory,
    topology,
    swarm_size: int,
    patience: int,
    max_iterations: int,
) -> None:
    """Ejecuta el mismo target con distintas semillas y compara gbest final."""
    print(f"\n    Comparación de semillas para target={target:+.6f}")
    print(f"    {'Semilla':>8}  {'gbest_final':>14}  {'iters':>6}  {'motivo':>15}  {'div_final':>10}  {'mov_final':>10}")
    print(f"    {'─'*8}  {'─'*14}  {'─'*6}  {'─'*15}  {'─'*10}  {'─'*10}")
    for seed in seeds:
        rng_np = np.random.default_rng(seed)
        vm = velocity_model_factory()
        result = pso(
            returns_matrix=returns_matrix,
            swarm_size=swarm_size,
            target_value=target,
            fitness_function=fitness_function,
            velocity_model=vm,
            topology=topology,
            patience=patience,
            max_iterations=max_iterations,
            random_generator=rng_np,
            return_diagnostics=True,
        )
        trace: ConvergenceTrace = result[-1]
        n = trace.iterations_completed
        gbest_f = trace.gbest[-1] if n > 0 else float("nan")
        div_f = trace.diversity[-1] if n > 0 else float("nan")
        mov_f = trace.movement_mean[-1] if n > 0 else float("nan")
        print(
            f"    {seed:>8}  {gbest_f:>14.8f}  {n:>6}  {trace.termination_reason:>15}  "
            f"{div_f:>10.6f}  {mov_f:>10.6f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Escenario 1: Sintético (mismo que tests)
# ─────────────────────────────────────────────────────────────────────────────

def run_synthetic() -> None:
    _header("ESCENARIO 1: Matriz sintética (4 obs × 3 activos) — mismo que tests PSO-01/PSO-02")
    print("""
  Propósito: observar el comportamiento del algoritmo en un caso completamente
  controlable. La matriz es pequeña; el espacio de búsqueda en el simplex 3D
  es reducido. Verás si hay colapso temprano, movimiento sin mejora, etc.
    """)

    returns = RETURNS_SYNTHETIC
    mean_ret = returns.mean(axis=0)
    lim_inf, lim_sup = mean_ret.min(), mean_ret.max()
    targets = np.linspace(lim_inf, lim_sup, 5)

    configs = [
        ("Variance / Inertia / Global",  Variance(),  lambda: Inertia(),       GlobalTopology()),
        ("Variance / Inertia / Ring",    Variance(),  lambda: Inertia(),       RingTopology()),
        ("CVaR    / Constriction / Ring", CVaR(),     lambda: Constriction(),  RingTopology()),
    ]

    for cfg_label, ff, vm_factory, topo in configs:
        _section(f"Configuración: {cfg_label}")
        for t in targets:
            rng = np.random.default_rng(99)
            vm = vm_factory()
            result = pso(
                returns_matrix=returns,
                swarm_size=10,
                target_value=t,
                fitness_function=ff,
                velocity_model=vm,
                topology=topo,
                patience=5,
                max_iterations=50,
                random_generator=rng,
                return_diagnostics=True,
            )
            trace: ConvergenceTrace = result[-1]
            _summarize_trace(trace, target=t, label=cfg_label, n_stages=4)

        # Comparación semillas para el target del medio
        mid_target = float(targets[len(targets) // 2])
        _section(f"Comparación de semillas — target medio ({mid_target:+.6f})")
        _compare_seeds(
            returns_matrix=returns,
            target=mid_target,
            seeds=[1, 2, 3, 4, 5],
            fitness_function=ff,
            velocity_model_factory=vm_factory,
            topology=topo,
            swarm_size=10,
            patience=5,
            max_iterations=50,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Escenario 2: Realista (200 obs × 4 activos)
# ─────────────────────────────────────────────────────────────────────────────

def run_realistic() -> None:
    _header("ESCENARIO 2: Matriz 'realista' (200 obs × 4 activos, semilla=42)")
    print("""
  Propósito: aproximar el comportamiento real que ves en Streamlit.
  200 períodos, 4 activos con medias y volatilidades distintas.
  Swarm más grande (30), parámetros similares a los predeterminados de la app.

  La pregunta clave: ¿el gbest ya no baja después de las primeras iteraciones?
  ¿La diversidad colapsa rápido? ¿El movimiento persiste sin mejora?
    """)

    returns = RETURNS_REALISTIC
    mean_ret = returns.mean(axis=0)
    lim_inf, lim_sup = mean_ret.min(), mean_ret.max()
    targets = np.linspace(lim_inf, lim_sup, 7)

    configs = [
        ("CVaR / Inertia / Global",      CVaR(),      lambda: Inertia(),      GlobalTopology()),
        ("Variance / Inertia / Global",   Variance(),  lambda: Inertia(),      GlobalTopology()),
        ("CVaR / Constriction / Ring",    CVaR(),      lambda: Constriction(), RingTopology()),
    ]

    for cfg_label, ff, vm_factory, topo in configs:
        _section(f"Configuración: {cfg_label}")
        for i, t in enumerate(targets):
            # Semillas distintas por target para no sesgar
            rng = np.random.default_rng(100 + i)
            vm = vm_factory()
            result = pso(
                returns_matrix=returns,
                swarm_size=30,
                target_value=t,
                fitness_function=ff,
                velocity_model=vm,
                topology=topo,
                patience=10,
                max_iterations=200,
                random_generator=rng,
                return_diagnostics=True,
            )
            trace: ConvergenceTrace = result[-1]
            label_with_pos = f"{cfg_label}  [punto {i}/{len(targets)-1}]"
            _summarize_trace(trace, target=t, label=label_with_pos, n_stages=6)

        # Comparación semillas para el target más bajo (bajo riesgo / baja ganancia)
        low_target = float(targets[0])
        _section(f"Comparación semillas — target BAJO ({low_target:+.6f}) — el caso que te intriga")
        _compare_seeds(
            returns_matrix=returns,
            target=low_target,
            seeds=[10, 20, 30, 40, 50],
            fitness_function=ff,
            velocity_model_factory=vm_factory,
            topology=topo,
            swarm_size=30,
            patience=10,
            max_iterations=200,
        )

        # Comparación semillas para el target más alto (alta ganancia / más riesgo)
        high_target = float(targets[-1])
        _section(f"Comparación semillas — target ALTO ({high_target:+.6f})")
        _compare_seeds(
            returns_matrix=returns,
            target=high_target,
            seeds=[10, 20, 30, 40, 50],
            fitness_function=ff,
            velocity_model_factory=vm_factory,
            topology=topo,
            swarm_size=30,
            patience=10,
            max_iterations=200,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnóstico de convergencia del PSO — salida descriptiva por target y semilla."
    )
    parser.add_argument(
        "--scenario",
        choices=["synthetic", "realistic", "all"],
        default="synthetic",
        help=(
            "synthetic: matriz 4×3 (igual que los tests, rápido). "
            "realistic: matriz 200×4 (aproxima Streamlit). "
            "all: ambos escenarios."
        ),
    )
    args = parser.parse_args()

    print()
    print("PSO — Diagnóstico de convergencia")
    print("Nota: este script no modifica tests ni src/. Solo ejecuta y observa.")
    print(THIN)

    if args.scenario in ("synthetic", "all"):
        run_synthetic()

    if args.scenario in ("realistic", "all"):
        run_realistic()

    print()
    print(SEP)
    print("  Diagnóstico completado.")
    print(SEP)
    print()


if __name__ == "__main__":
    main()
