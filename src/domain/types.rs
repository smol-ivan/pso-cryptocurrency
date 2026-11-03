use ndarray::Array1;
use yahoo_finance_api::Quote;

/// Represents the portfolio weights assigned to each asset.
///
/// Each element corresponds to an asset in the same order as the
/// associated dataset.
pub type Weights = Array1<f64>;

/// Represents the momentum component of a particle's velocity.
///
/// Stores the per-dimension momentum values used by the PSO algorithm.
pub type Momentums = Array1<f64>;

/// Represents a collection of historical market quotes retrieved
/// from Yahoo Finance.
pub type Quotes = Vec<Quote>;
