mod fitness;
mod particle;
mod pso;
mod types;
mod velocity;

use crate::pso::Pso;

fn main() {
    println!("Hello, world!");
    let pso = Pso::default();
    pso.optimization();
}
