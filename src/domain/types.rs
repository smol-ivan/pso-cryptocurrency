use ndarray::Array1;
use yahoo_finance_api::Quote;

pub type Weights = Array1<f64>;
pub type Momentums = Array1<f64>;

pub type Quotes = Vec<Quote>;
