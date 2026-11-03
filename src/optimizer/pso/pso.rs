use anyhow::Result;
use ndarray::{Array1, Array2};
use ndarray_rand::RandomExt;
use ndarray_rand::rand_distr::Uniform;

use super::fitness::FitnessFunction;
use super::particle::Particle;
use super::velocity::VelocityModel;
use crate::domain::types::{Momentums, Weights};

// TODO: Define how non-finite fitness values are handled
// during global best selection.

/// Particle swarm optimization engine for portfolio optimization.
///
/// The optimizer coordinates particle initialization, fitness evaluation,
/// global best selection, and particle movement throughout the optimization
/// process.
///
/// Fitness evaluation and velocity updates are delegated to configurable
/// strategy implementations.
pub struct Pso {
    /// Fitness function used to evaluate candidate portfolios.
    fitness_function: Box<dyn FitnessFunction>,

    /// Velocity update strategy used to move particles.
    velocity_model: Box<dyn VelocityModel>,

    /// Number of dimensions in the search space.
    ///
    /// For portfolio optimization, this corresponds to the number of assets.
    dimensions: usize,

    /// Number of particles in the swarm
    swarm_size: usize,

    /// Historical asset returns used during fitness evaluation.
    ///
    /// Rows represent observations and columns represent assets.
    returns: Array2<f64>,

    /// Minimum expected portfolio return required by the fitness function.
    target_return: f64,
}

impl Pso {
    /// Creates a PSO optimizer with the provided strategies and parameters.
    ///
    /// # Arguments
    ///
    /// * `fitness_function` - Strategy used to evaluate candidate portfolios.
    /// * `velocity_model` - Strategy used to update particle velocities and positions.
    /// * `dimensions` - Number of dimensions in the search space.
    /// * `swarm_size` - Number of particles in the swarm.
    /// * `returns` - Historical asset returns, with observations as rows
    ///   and assets as columns.
    /// * `target_return` - Minimum expected portfolio return.
    pub fn new(
        fitness_function: Box<dyn FitnessFunction>,
        velocity_model: Box<dyn VelocityModel>,
        dimensions: usize,
        swarm_size: usize,
        returns: Array2<f64>,
        target_return: f64,
    ) -> Self {
        Pso {
            fitness_function,
            velocity_model,
            dimensions,
            swarm_size,
            returns,
            target_return,
        }
    }

    /// Executes the particle swarm optimization process.
    ///
    /// The method initializes the swarm, evaluates particle fitness,
    /// updates the global best solution, and applies the configured
    /// velocity model over a fixed number of iterations.
    ///
    /// Particle fitness is minimized throughout the optimization process.
    pub fn optimization(&self) -> Result<Particle> {
        let mut swarm = self.init_swarm();
        let mut best_global = swarm[0].clone(); // Escoger cualquier particula para empezar

        // TODO: Replace the fixed iteration count with a configurable
        // stopping criterion.
        for _ in 0..100 {
            // evaluar cada particula
            swarm.iter_mut().for_each(|p| {
                p.evaluate_fitness(
                    self.fitness_function.as_ref(),
                    &self.returns,
                    self.target_return,
                )
            });

            self.find_best_global(&swarm, &mut best_global);

            //TODO: actualizar posicion dada la velocidad y normalizar
            for particle in &mut swarm {
                self.velocity_model
                    .update(particle, &best_global, self.dimensions);
            }
        }
        Ok(best_global)
    }

    /// Initializes the particle swarm.
    ///
    /// Each particle receives a random position in the search space
    /// and an initial velocity vector filled with zeros.
    ///
    /// # Returns
    ///
    /// A vector containing the initialized particles.
    fn init_swarm(&self) -> Vec<Particle> {
        (0..self.swarm_size)
            .map(|_| {
                let mut position: Weights =
                    Array1::<f64>::random(self.dimensions, Uniform::new(0., 1.).unwrap());
                self.velocity_model.repair_position(&mut position);
                let velocity: Momentums = Array1::<f64>::zeros(self.dimensions);

                Particle::new(&position, &velocity)
            })
            .collect()
    }

    /// Updates the global best particle if a better personal best is found.
    ///
    /// The particle with the lowest personal best fitness value is selected
    /// and compared against the current global best.
    ///
    /// # Arguments
    ///
    /// * `swarm` - Current population of particles.
    /// * `best_global` - Mutable reference to the global best particle.
    fn find_best_global(&self, swarm: &[Particle], best_global: &mut Particle) {
        let best_iter = swarm
            .iter()
            .min_by(|a, b| a.best_value.partial_cmp(&b.best_value).unwrap())
            .unwrap();

        if best_iter.best_value < best_global.best_value {
            *best_global = best_iter.clone()
        }
    }
}
