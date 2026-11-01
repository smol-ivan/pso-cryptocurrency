mod optimizer;

use optimizer::pso::Pso;
use tokio;

#[tokio::main]
async fn main() {
    println!("Hello, world!");
    let pso = Pso::default();
    pso.optimization();
}
