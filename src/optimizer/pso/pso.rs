use ndarray::Array1;
use ndarray_rand::RandomExt;
use ndarray_rand::rand_distr::Uniform;

use super::fitness::{FitnessFunction, Variance};
use super::particle::Particle;
use super::types::{Momentums, Weights};
use super::velocity::{InertiaM, VelocityModel};

pub struct Pso {
    fitness_function: Box<dyn FitnessFunction>,
    velocity_model: Box<dyn VelocityModel>,
    dimensions: usize,
    swarm_size: usize,
}

impl Default for Pso {
    fn default() -> Self {
        Pso {
            fitness_function: Box::new(Variance::default()),
            velocity_model: Box::new(InertiaM::default()),
            dimensions: 4,
            swarm_size: 3,
        }
    }
}

impl Pso {
    pub fn optimization(&self) {
        let mut swarm = self.init_swarm();
        let mut best_global = swarm[0].clone(); // Escoger cualquier particula para empezar

        self.find_best_global(&swarm, &mut best_global);

        //TODO: cambiar for por while
        // Eso implica paro por convergencia
        for _ in 0..1 {
            // evaluar cada particula
            swarm
                .iter_mut()
                .for_each(|p| p.evaluate_fitness(self.fitness_function.as_ref()));

            // TODO: Encontrar al mejor absoluto

            self.find_best_global(&swarm, &mut best_global);

            //TODO: actualizar posicion dada la velocidad y normalizar
            for particle in &mut swarm {
                self.velocity_model
                    .update(particle, &best_global, self.dimensions);
            }
        }
        println!("{:#?}", swarm);
    }

    /// Hello to all my rabies!
    ///
    /// - Basically we give each particle a randon start position (each dimension from 0 to 1)
    /// and everyone start with velocity zero
    ///
    fn init_swarm(&self) -> Vec<Particle> {
        (0..self.swarm_size)
            .map(|_| {
                let position: Weights =
                    Array1::<f64>::random(self.dimensions, Uniform::new(0., 1.).unwrap());
                let velocity: Momentums = Array1::<f64>::zeros(self.dimensions);

                Particle::new(&position, &velocity)
            })
            .collect()
    }

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
