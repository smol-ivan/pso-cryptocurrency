use anyhow::Result;
use ndarray::{Array1, Array2};
use ndarray_rand::RandomExt;
use ndarray_rand::rand_distr::Uniform;

use ndarray_rand::rand::SeedableRng;
use ndarray_rand::rand::rngs::StdRng;

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

    /// Number of iteratios given to the optimization
    iterations: usize,

    /// Seeded pseudo-random number generator for deterministic optimization.
    rng: StdRng,
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
    /// * `iterations` - Number of iterations for the optimization.
    /// * `seed` - Seed value for deterministic pseudo-random number generation.
    pub fn new(
        fitness_function: Box<dyn FitnessFunction>,
        velocity_model: Box<dyn VelocityModel>,
        dimensions: usize,
        swarm_size: usize,
        returns: Array2<f64>,
        target_return: f64,
        iterations: usize,
        rng: StdRng,
    ) -> Self {
        Pso {
            fitness_function,
            velocity_model,
            dimensions,
            swarm_size,
            returns,
            target_return,
            iterations,
            rng,
        }
    }

    /// Executes the particle swarm optimization process.
    ///
    /// The method initializes the swarm, evaluates particle fitness,
    /// updates the global best solution, and applies the configured
    /// velocity model over a fixed number of iterations.
    ///
    /// Particle fitness is minimized throughout the optimization process.
    pub fn optimization(&mut self) -> Result<Particle> {
        let mut swarm = self.init_swarm();
        let mut best_global = swarm[0].clone(); // Escoger cualquier particula para empezar

        // TODO: Replace the fixed iteration count with a configurable
        // stopping criterion.
        for _ in 0..self.iterations {
            // evaluar cada particula
            let improved_pbest = swarm
                .iter_mut()
                .map(|p| {
                    p.evaluate_fitness(
                        self.fitness_function.as_ref(),
                        &self.returns,
                        self.target_return,
                    )
                })
                .filter(|&improved| improved)
                .count();

            let gbest_improved = self.find_best_global(&swarm, &mut best_global);

            //TODO: actualizar posicion dada la velocidad y normalizar
            for particle in &mut swarm {
                self.velocity_model
                    .update(particle, &best_global, self.dimensions, &mut self.rng);
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
    fn init_swarm(&mut self) -> Vec<Particle> {
        let dimensions = self.dimensions;
        let rng = &mut self.rng;
        (0..self.swarm_size)
            .map(|_| {
                let mut position: Weights =
                    Array1::<f64>::random_using(dimensions, Uniform::new(0., 1.).unwrap(), rng);
                self.velocity_model.repair_position(&mut position);
                let velocity: Momentums = Array1::<f64>::zeros(dimensions);

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
    fn find_best_global(&self, swarm: &[Particle], best_global: &mut Particle) -> bool {
        let best_iter = swarm
            .iter()
            .min_by(|a, b| a.best_eval.fitness.total_cmp(&b.best_eval.fitness))
            .unwrap();

        if best_iter.best_eval.fitness < best_global.best_eval.fitness {
            *best_global = best_iter.clone();
            return true;
        }
        false
    }
}

#[cfg(test)]
mod tests {
    use ndarray::array;

    use super::*;
    use crate::config::{InertiaParams, VarianceParams};
    use crate::optimizer::pso::fitness::{PenalizedFitness, PenaltyParams, Variance, VarianceRisk};
    use crate::optimizer::pso::velocity::InertiaM;

    #[test]
    fn replacement_preserves_seeded_optimization_result() {
        let returns = array![
            [0.01, 0.02, -0.01],
            [0.03, -0.02, 0.04],
            [-0.01, 0.01, 0.02],
            [0.02, 0.03, -0.03],
        ];
        let velocity = InertiaParams {
            c1: 0.5,
            c2: 0.9,
            inertia: 0.8,
        };
        let legacy = Variance::new(VarianceParams {
            penalty: 50.0,
            eps: 1e-6,
        });
        let replacement = PenalizedFitness::new(
            Box::new(VarianceRisk),
            PenaltyParams {
                penalty: 50.0,
                eps: 1e-6,
            },
        );

        let mut legacy_pso = Pso::new(
            Box::new(legacy),
            Box::new(InertiaM::new(velocity.clone())),
            3,
            5,
            returns.clone(),
            0.02,
            10,
            StdRng::seed_from_u64(7),
        );
        let mut replacement_pso = Pso::new(
            Box::new(replacement),
            Box::new(InertiaM::new(velocity)),
            3,
            5,
            returns,
            0.02,
            10,
            StdRng::seed_from_u64(7),
        );

        let legacy_best = legacy_pso.optimization().unwrap();
        let replacement_best = replacement_pso.optimization().unwrap();

        assert_eq!(
            legacy_best.best_eval.fitness,
            replacement_best.best_eval.fitness
        );
    }
}
