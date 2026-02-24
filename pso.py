from enum import Enum
from random import random
from typing import override

import numpy as np


class OptimizationMode(Enum):
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_RETURN = "maximize_return"


def pso(mean_return, returns_matrix, iter, n_swarm, mode, c1, c2, target_value):
    swarm = swarm_init(
        mean_return.shape[0], returns_matrix, mean_return, n_swarm, mode, target_value
    )

    best_g_pos, best_g_val = get_best_particle(swarm)

    for _ in range(iter):
        for particle in swarm:
            update_particle(
                particle, best_g_pos, mean_return, returns_matrix, target_value, mode
            )

        best_iter_pos, best_iter_val = get_best_particle(swarm)

        if best_iter_val < best_g_val:
            best_g_pos = best_iter_pos.copy()
            best_g_val = best_iter_val

    return best_g_val, best_g_pos
    # EActualmente el mejor valor es el fitnes, o sea el riesgo (varianza del partafolio)
    # la posicion es cuanto tenemos invertido en cada activo
    # el retorno se calcula con el producto punto


def swarm_init(n_assets, returns_matrix, mean_return, n_swarm, mode, target_value):
    swarm = []
    for _ in range(n_swarm):
        position = np.random.rand(n_assets)
        position = normalization(position)
        velocity = np.zeros(n_assets)
        fitness = fitness_function(
            position, mean_return, returns_matrix, mode, target_value
        )

        swarm.append(Particle(position, velocity, fitness))

    return swarm


def compute_cvar(position, returns_matrix, alpha=0.99):
    """
    position: Vector de pesos (N,)
    returns_matrix: Matriz de retornos historicos (T x N)
    """
    # Retornos del portafolio para todos los dias
    portafolio_returns = returns_matrix @ position

    # VaR (Percentil de la cola izquierda)
    var_threshold = np.percentile(portafolio_returns, (1 - alpha) * 100)

    # Cola de perdidas
    tails_losses = portafolio_returns[portafolio_returns <= var_threshold]

    # CVaR = promedio de la cola
    cvar = tails_losses.mean()

    return cvar, portafolio_returns.mean()


def fitness_function(
    position,
    mean_return,
    returns_matrix,
    mode,
    target_value,
    penalty=1e4,
):
    """
    Fitness basada en CVaR
    """
    cvar, p_return = compute_cvar(position, returns_matrix)

    # cvar es negativo (maneja perdidas)
    risk = -cvar

    if mode == OptimizationMode.MINIMIZE_RISK:
        fitness = risk  # + penalizacion por peso negativo

        if p_return < target_value:
            diff = target_value - p_return
            fitness += penalty * (diff**2)

    else:
        # Minimizar el negativo del retorno
        # Maximizar retorno bajo riesgo maximo permitido
        fitness = -p_return

        if risk > target_value:
            diff = risk - target_value
            fitness += penalty * (diff**2)

    return fitness
    # Se piensa en si el fitness es mejor
    # fitness > g_best_fitness
    # minimizamos el riesgo, valores ~0 son mejor


def update_particle(
    p,
    best_g_pos,
    mean_return,
    returns_matrix,
    target_value,
    mode,
    C1=0.5,
    C2=1.0,
    INERTIA=0.8,
):
    """
    Actualizacion de velocidad tomando en cuenta los mejores particulas globales
    TODO(Ver si es necesario copiar el arreglo np para estas operaciones)
    """
    r1 = random()
    r2 = random()
    new_velocity = (
        (INERTIA * p.velocity)
        + (C1 * r1 * (p.best_pos - p.position))
        + (C2 * r2 * (best_g_pos - p.position))
    )
    p.velocity = new_velocity
    new_position = p.position + p.velocity
    p.position = normalization(new_position)

    new_fitness = fitness_function(
        p.position, mean_return, returns_matrix, mode, target_value
    )
    # print(new_fitness)

    if new_fitness < p.best_val:
        p.best_val = new_fitness
        p.best_pos = p.position.copy()


class Particle:
    def __init__(
        self,
        position,
        velocity,
        fitness_value,
    ):
        self.position = position.copy()
        self.velocity = velocity.copy()
        self.best_pos = self.position.copy()
        self.best_val = fitness_value

    @override
    def __str__(self) -> str:
        return f"Position: {self.position}\nValue: {self.best_val}"


def normalization(position):
    position = np.maximum(0, position)

    total_weight = np.sum(position)
    if total_weight > 0:
        position /= total_weight

    return position


def get_best_particle(swarm):
    best_p = min(swarm, key=lambda p: p.best_val)
    return best_p.best_pos, best_p.best_val
