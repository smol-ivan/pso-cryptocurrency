mod market_data;
mod optimizer;
mod domain;

use optimizer::pso::Pso;
use time::macros::datetime;
use tokio;

use crate::market_data::provider::download;

#[tokio::main]
async fn main() {
    println!("Hello, world!");
    let pso = Pso::default();
    pso.optimization();
    let start = datetime!(2024-1-1 0:00:00.00 UTC);
    let end = datetime!(2024-1-5 23:59:59.99 UTC);
    let tickers = vec!["NVDA".to_string()];
    let res = download(start, end, &tickers).await.unwrap();
    println!("{:#?}", res)
}
