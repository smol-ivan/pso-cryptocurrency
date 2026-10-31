use crate::fitness::FitnessFunction;
use crate::types::{Momentums, Weights};

#[derive(Debug, Clone)]
pub struct Particle {
    pub position: Weights,
    pub velocity: Momentums,
    pub best_position: Weights,
    pub best_value: f64,
    pub value: f64,
}

impl Default for Particle {
    fn default() -> Self {
        Particle {
            position: Vec::new().into(),
            velocity: Vec::new().into(),
            best_position: Vec::new().into(),
            best_value: f64::INFINITY,
            value: f64::INFINITY,
        }
    }
}

impl Particle {
    pub fn new(position: &Weights, velocity: &Momentums) -> Self {
        Particle {
            position: position.clone(),
            velocity: velocity.clone(),
            best_position: position.clone(),
            best_value: f64::INFINITY,
            value: f64::INFINITY,
        }
    }

    pub fn evaluate_fitness(&mut self, function: &dyn FitnessFunction) {
        let fitness_value = function.get_fitness(&self.position);

        self.value = fitness_value;

        if fitness_value < self.best_value {
            self.best_position = self.position.clone();
            self.best_value = fitness_value;
        }
    }
}
