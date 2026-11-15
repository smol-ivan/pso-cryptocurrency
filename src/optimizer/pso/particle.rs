use ndarray::Array2;

use super::fitness::FitnessFunction;
use crate::domain::{
    Evaluation,
    types::{Momentums, Weights},
};

/// Represents a particle in the particle swarm optimization algorithm.
///
/// A particle stores its current position and velocity, along with
/// its current fitness value and the best position found during
/// its individual search history.
#[derive(Debug, Clone)]
pub struct Particle {
    /// Current position of the particle in the search space.
    ///
    /// Each dimension represents the portfolio weight assigned
    /// to the corresponding asset.
    pub position: Weights,

    /// Current velocity of the particle.
    ///
    /// Stores the movement component for each dimension of the
    /// search space.
    pub velocity: Momentums,

    /// Best position found by this particle so far.
    pub best_position: Weights,

    /// Best Evaluation achieved by this particle.
    pub best_eval: Evaluation,

    /// Evaluation of the particle's current position.
    pub eval: Evaluation,
}

impl Particle {
    /// Creates a particle from an initial position and velocity.
    ///
    /// The initial position is also assigned as the particle's
    /// personal best position. Both evaluations are initialized with
    /// [`Evaluation::default`] and must be evaluated afterward.
    ///
    /// # Arguments
    ///
    /// * `position` - Initial position in the search space.
    /// * `velocity` - Initial velocity of the particle.
    pub fn new(position: &Weights, velocity: &Momentums) -> Self {
        Particle {
            position: position.clone(),
            velocity: velocity.clone(),
            best_position: position.clone(),
            best_eval: Evaluation::default(),
            eval: Evaluation::default(),
        }
    }

    /// Evaluates the particle's current position and updates its personal best.
    ///
    /// The current position is evaluated using the provided fitness function.
    /// If the resulting fitness value is lower than the particle's previous
    /// best value, the current position becomes its new personal best.
    ///
    /// # Arguments
    ///
    /// * `function` - Fitness function used to evaluate the particle.
    /// * `returns` - Historical asset returns, with observations as rows
    ///   and assets as columns.
    /// * `target_return` - Minimum expected portfolio return.
    ///
    /// # Notes
    ///
    /// The particle's personal best is updated only when the new fitness
    /// value is strictly lower than its previous best.
    ///
    /// $$
    /// pbest_i^{(t)} =
    /// \begin{cases}
    /// x_i^{(t)}, & \text{si } f_i^{(t)} < pbestValue_i^{(t-1)}\\
    /// pbest_i^{(t-1)}, & \text{en otro caso}
    /// \end{cases}
    /// $$
    pub fn evaluate_fitness(
        &mut self,
        function: &dyn FitnessFunction,
        returns: &Array2<f64>,
        target_return: f64,
    ) -> bool {
        // TODO: Validate particle dimensions against the provided return matrix.
        let new_eval = function.get_fitness(&self.position, &returns, target_return);

        // TODO: Define how non-finite fitness values should be handled.
        let improved = new_eval.fitness < self.best_eval.fitness;

        if improved {
            self.best_position = self.position.clone();
            self.best_eval = new_eval.clone();
        }

        self.eval = new_eval;

        improved
    }
}
