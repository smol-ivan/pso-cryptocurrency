use super::particle::Particle;
use crate::domain::types::Weights;
use ndarray_rand::RandomExt;

use ndarray::Array1;

use ndarray_rand::rand;
use ndarray_rand::rand_distr::Uniform;

/// Defines the interface for particle velocity update strategies.
///
/// Implementations determine how particle velocities and positions
/// evolve during the PSO optimization process. They also provide
/// a mechanism to repair positions according to the search-space
/// constraints.
pub trait VelocityModel {
    /// Updates a particle's velocity and position.
    ///
    /// # Arguments
    ///
    /// * `particle` - Particle whose velocity and position will be updated.
    /// * `best_global` - Particle representing the best global solution found.
    /// * `dimension` - Number of dimensions in the search space.
    fn update(&self, particle: &mut Particle, best_global: &Particle, dimension: usize);

    /// Repairs a particle position to satisfy the search-space constraints.
    ///
    /// # Arguments
    ///
    /// * `position` - Mutable particle position to repair.
    fn repair_position(&self, position: &mut Weights);
}

/// Particle velocity update strategy based on the inertia weight model.
///
/// The model combines the particle's previous velocity, its personal
/// best position, and the global best position to determine its
/// next movement.
pub struct InertiaM {
    /// Cognitive acceleration coefficient.
    pub c1: f64,

    /// Social acceleration coefficient.
    pub c2: f64,

    /// Inertia weight controlling the influence of the previous velocity.
    pub inertia: f64,
}

impl Default for InertiaM {
    /// Creates an inertia-based velocity model with default coefficients.
    ///
    /// The default configuration uses:
    /// - Cognitive coefficient: 0.5.
    /// - Social coefficient: 0.9.
    /// - Inertia weight: 0.8.
    fn default() -> Self {
        Self {
            c1: 0.5,
            c2: 0.9,
            inertia: 0.8,
        }
    }
}

impl VelocityModel for InertiaM {
    /// Updates a particle's velocity and position using the inertia-based model.
    ///
    /// Random acceleration vectors are generated for the cognitive and social
    /// components. The resulting velocity is added to the current position,
    /// which is subsequently repaired to satisfy the portfolio weight constraints.
    ///
    /// # Arguments
    ///
    /// * `particle` - Particle to update.
    /// * `best_global` - Global best particle used by the social component.
    /// * `dimension` - Number of dimensions used to generate the random vectors.
    fn update(&self, particle: &mut Particle, best_global: &Particle, dimension: usize) {
        // TODO: Verify random number generation consistency with the optimizer seed policy.
        let mut rng = rand::rng();

        // Generate random acceleration vectors for the cognitive and social components.
        let r1 = Array1::<f64>::random_using(dimension, Uniform::new(0.0, 1.0).unwrap(), &mut rng);
        let r2 = Array1::<f64>::random_using(dimension, Uniform::new(0.0, 1.0).unwrap(), &mut rng);

        let inertia_cmp = self.inertia * &particle.velocity;
        let personal_cmp = self.c1 * &r1 * (&particle.best_position - &particle.position);
        let social_cmp = self.c2 * &r2 * (&best_global.position - &particle.best_position);

        particle.velocity = inertia_cmp + personal_cmp + social_cmp;
        particle.position += &particle.velocity;

        //TODO: normalizar posiciones por reestriccion de pesos ponderados = 1
        self.repair_position(&mut particle.position);
    }

    /// Repairs a particle position to satisfy portfolio weight constraints.
    ///
    /// Negative weights are clipped to zero, and the remaining values
    /// are normalized so that their sum equals one.
    ///
    /// If all weights are zero after clipping, a uniform allocation
    /// is assigned across all dimensions.
    ///
    /// # Arguments
    ///
    /// * `position` - Mutable vector of portfolio weights to repair.
    fn repair_position(&self, position: &mut Weights) {
        // Clip negative weights to enforce non-negative allocations.
        position.mapv_inplace(|x| x.max(0.0));

        let sum = position.sum();

        // We do not like division by zero
        // Edge case consideration
        // TODO: Validate non-finite position values before normalization.
        if sum > 0.0 {
            // Normalize weights to ensure their sum equals one.
            *position /= sum;
        } else {
            // Assign a uniform allocation when all weights are zero.
            let n = position.len() as f64;
            position.fill(1. / n);
        }
    }
}
