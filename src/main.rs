use ndarray::prelude::*;
use ndarray::{Array, Array1};
use ndarray_rand::rand_distr::Uniform;
use ndarray_rand::{RandomExt, rand};
use rand::Rng;

fn main() {
    println!("Hello, world!");
    pso();
}

#[derive(Debug, Clone)]
struct Particle {
    position: Array1<f64>,
    velocity: Array1<f64>,
    best_position: Array1<f64>,
    best_value: f64,
    fitness_value: f64,
}

impl Default for Particle {
    fn default() -> Self {
        Particle {
            position: Vec::new().into(),
            velocity: Vec::new().into(),
            best_position: Vec::new().into(),
            best_value: f64::INFINITY,
            fitness_value: f64::INFINITY,
        }
    }
}

impl Particle {
    fn new(position: &Array1<f64>, velocity: &Array1<f64>, fitness_value: f64) -> Self {
        Particle {
            position: position.clone(),
            velocity: velocity.clone(),
            best_position: position.clone(),
            best_value: fitness_value,
            fitness_value,
        }
    }

    /// Update fitness value & best personal position (if changes)
    /// TODO: should change name funcition that fits the work that it does
    fn update_fitness_value(&mut self, function: &dyn FitnessFunction) {
        // TODO actualizar la mejor posicion personal
        let fitness_value = function.evaluate(&self.position);

        self.fitness_value = fitness_value;
    }
}

/// Hello to all my rabies!
///
/// - Basically we give each particle a randon start position (each dimension/active from 0 to 1)
/// and everyone start with velocity zero
///
/// - Also we do not normalize!
fn init_swarm(swarm_n: usize, dim: usize) -> Vec<Particle> {
    (0..swarm_n)
        .map(|_| {
            let position = Array1::<f64>::random(dim, Uniform::new(0., 1.).unwrap());
            let velocity = Array1::<f64>::zeros(dim);

            Particle::new(&position, &velocity, 1.0)
        })
        .collect()
}

trait FitnessFunction {
    fn evaluate(&self, position: &Array1<f64>) -> f64;
}

struct Variance;

impl FitnessFunction for Variance {
    fn evaluate(&self, position: &Array1<f64>) -> f64 {
        // TODO: swarm size value should be know for the calculations
        let n = position.len() as f64;
        if n == 0.0 {
            return 0.0;
        }

        let mean = position.mean().unwrap_or(0.0);
        let var = position.mapv(|x| (x - mean).powi(2)).sum() / n;

        var
    }
}

trait VelocityModel {
    fn update(&self, particle: &mut Particle, best_g: &Array1<f64>);
}

struct InertiaM {
    c1: f64,
    c2: f64,
    inertia: f64,
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
    fn update(&self, particle: &mut Particle, best_g: &Array1<f64>) {
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
        let social_cmp = self.c2 * &r2 * (&particle.best_position - best_g);

        particle.velocity = inertia_cmp + personal_cmp + social_cmp;
        particle.position += &particle.velocity;

        //TODO: normalizar posiciones por reestriccion de pesos ponderados = 1
    }
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
    let fitness_function: Box<dyn FitnessFunction> = Box::new(Variance);
    // swarm inizialitation
    let dimensions = 2; // numero de variables de decision. Activos en nuestro caso
    let mut swarm = init_swarm(3, dimensions);
    println!("{:#?}", swarm);
    let mut best_global = Particle::default();
    for _ in 0..50 {
        // evaluar cada particula
        swarm
            .iter_mut()
            .map(|p| {
                p.update_fitness_value(fitness_function.as_ref());
            })
            .collect::<Vec<_>>();

        // TODO: Encontrar al mejor absoluto

        find_best_global(&swarm, &mut best_global);

        //TODO: actualizar posicion dada la velocidad y normalizar
    }

    println!(":#?", swarm);
}
