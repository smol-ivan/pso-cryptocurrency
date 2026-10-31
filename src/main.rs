mod fitness;
mod particle;
mod types;
mod velocity;

use crate::fitness::FitnessFunction;
use crate::fitness::Variance;
use crate::particle::Particle;
use crate::types::Momentums;
use crate::types::Weights;
use crate::velocity::InertiaM;
use crate::velocity::VelocityModel;
use ndarray::Array1;
use ndarray_rand::RandomExt;
use ndarray_rand::rand_distr::Uniform;

fn main() {
    println!("Hello, world!");
    pso();
}

/// Hello to all my rabies!
///
/// - Basically we give each particle a randon start position (each dimension from 0 to 1)
/// and everyone start with velocity zero
///
/// - Also we do not normalize here
fn init_swarm(swarm_n: usize, dim: usize) -> Vec<Particle> {
    (0..swarm_n)
        .map(|_| {
            let position: Weights = Array1::<f64>::random(dim, Uniform::new(0., 1.).unwrap());
            let velocity: Momentums = Array1::<f64>::zeros(dim);

            Particle::new(&position, &velocity)
        })
        .collect()
}

fn find_best_global(swarm: &[Particle], best_global: &mut Particle) {
    let best_iter = swarm
        .iter()
        .min_by(|a, b| a.best_value.partial_cmp(&b.best_value).unwrap())
        .unwrap();

    if best_iter.best_value < best_global.best_value {
        *best_global = best_iter.clone()
    }
}

fn pso() {
    // configuracion should be given by arg
    let fitness_function: Box<dyn FitnessFunction> = Box::new(Variance::default());
    let velocity_model: Box<dyn VelocityModel> = Box::new(InertiaM::default());

    // swarm inizialitation
    let dimensions = 2; // numero de variables de decision. Activos en nuestro caso
    let mut swarm = init_swarm(10, dimensions);
    // println!("{:#?}", swarm);
    let mut best_global = swarm[0].clone();

    find_best_global(&swarm, &mut best_global);

    for _ in 0..1 {
        // evaluar cada particula
        swarm
            .iter_mut()
            .for_each(|p| p.evaluate_fitness(fitness_function.as_ref()));

        // TODO: Encontrar al mejor absoluto

        find_best_global(&swarm, &mut best_global);

        //TODO: actualizar posicion dada la velocidad y normalizar
        for particle in &mut swarm {
            velocity_model.update(particle, &best_global);
        }
    }
    println!("{:#?}", swarm);
}
