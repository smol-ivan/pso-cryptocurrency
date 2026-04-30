from typing import List
import numpy as np

from models.particle import Particle

from models.fitness_function import FuncionObjetivo
from models.topology import Topologia
from models.velocity_model import ModeloVelocidad


def pso(
        returns_matrix: np.ndarray,
        iteraciones: int,
        n_swarm: int,
        target_value: float,
        funcion_objetivo: FuncionObjetivo,
        modelo_velocidad: ModeloVelocidad,
        topologia: Topologia
        ):

    n_assets= returns_matrix.shape[1]

    swarm: List["Particle"] = []
    for _ in range(n_swarm):
        position = np.random.rand(n_assets)
        if np.sum(position) > 0: 
            position /= np.sum(position)
        velocity = np.zeros(n_assets)
        fitness = funcion_objetivo.evaluar(position, returns_matrix, target_value)
        swarm.append(Particle(position, velocity, fitness))

    # INICIALIZACION

    # Mejor global ABSOLUTO
    mejor_particula_absoluta = min(swarm, key=lambda p: p.best_val)
    best_g_pos = mejor_particula_absoluta.best_pos.copy()
    best_g_val = mejor_particula_absoluta.best_val

    # CICLO OPTIMIZACION
    for _ in range(iteraciones):
        for idx, particle in enumerate(swarm):
            mejor_referencia = topologia.get_best_particle(idx, swarm)
            
            # B) Actualizar velocidad hacia esa referencia (Anillo, Global, etc.)
            modelo_velocidad.actualizar(particle, mejor_referencia)
            
            # C) Evaluar nueva posición
            new_fitness = funcion_objetivo.evaluar(particle.position, returns_matrix, target_value)
            
            # Actualizar mejor personal
            if new_fitness < particle.best_val:
                particle.best_val = new_fitness
                particle.best_pos = particle.position.copy()

        # Al final de la iteración, revisamos si alguien superó el récord histórico absoluto
        mejor_iteracion = min(swarm, key=lambda p: p.best_val)
        if mejor_iteracion.best_val < best_g_val:
            best_g_pos = mejor_iteracion.best_pos.copy()
            best_g_val = mejor_iteracion.best_val

    return best_g_val, best_g_pos

