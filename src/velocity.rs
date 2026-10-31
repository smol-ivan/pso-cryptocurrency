use crate::particle::Particle;
use crate::types::Weights;
use ndarray_rand::RandomExt;

use ndarray::Array1;

use ndarray_rand::rand;
use ndarray_rand::rand_distr::Uniform;

pub trait VelocityModel {
    fn update(&self, particle: &mut Particle, best_global: &Particle);
    fn repair_position(&self, position: &mut Weights);
}

pub struct InertiaM {
    pub c1: f64,
    pub c2: f64,
    pub inertia: f64,
}

impl Default for InertiaM {
    fn default() -> Self {
        Self {
            c1: 0.5,
            c2: 0.9,
            inertia: 0.8,
        }
    }
}

impl VelocityModel for InertiaM {
    fn update(&self, particle: &mut Particle, best_global: &Particle) {
        //TODO: temporary hardcoded dimensionality value.
        // best to look on how to pass that value bc we know it and we do not
        // need to calculate each time
        let dim = 2;

        let mut rng = rand::rng();

        // Generation or random vectors r1,r2
        let r1 = Array1::<f64>::random_using(dim, Uniform::new(0.0, 1.0).unwrap(), &mut rng);
        let r2 = Array1::<f64>::random_using(dim, Uniform::new(0.0, 1.0).unwrap(), &mut rng);

        let inertia_cmp = self.inertia * &particle.velocity;
        let personal_cmp = self.c1 * &r1 * (&particle.best_position - &particle.position);
        let social_cmp = self.c2 * &r2 * (&particle.best_position - &best_global.position);

        particle.velocity = inertia_cmp + personal_cmp + social_cmp;
        particle.position += &particle.velocity;

        //TODO: normalizar posiciones por reestriccion de pesos ponderados = 1
    }

    /// Call for an ambulance for those that are outa bounds!
    fn repair_position(&self, position: &mut Weights) {
        // Cutoff any value below zero
        // if it is, reset to zero
        position.mapv_inplace(|x| x.max(0.0));

        let sum = position.sum();

        // We do not like division by zero
        // Edge case consideration
        if sum > 0.0 {
            // Always normalize
            *position /= sum;
        } else {
            let n = position.len() as f64;
            position.fill(x);
        }
    }
}
