use anyhow::Result;
use ndarray::Axis;

use crate::domain::types::Quotes;

/// Represents a financial asset along with its historical market quotes.
///
/// The structure stores the asset's identifying information and the
/// historical quotes retrieved for a specific date range.
#[derive(Debug)]
pub struct AssetModel {
    /// Asset ticker symbol.
    pub symbol: String,

    /// Asset name, usually obtained from the data provider.
    pub name: String,

    /// Historical market quotes associated with the asset.
    pub quotes: Quotes,
}

impl AssetModel {
    /// Creates a new asset model.
    ///
    /// # Arguments
    ///
    /// * `symbol` - Asset ticker symbol.
    /// * `name` - Asset name.
    /// * `quotes` - Historical market quotes associated with the asset.
    pub fn new(symbol: String, name: String, quotes: Quotes) -> AssetModel {
        AssetModel {
            symbol,
            name,
            quotes,
        }
    }
}

/// Represents a historical financial dataset prepared for portfolio analysis.
///
/// The dataset contains an ordered list of assets, their corresponding
/// observation timestamps, and a matrix of historical returns.
///
/// The return matrix uses observations as rows and assets as columns.
/// Each column corresponds to an asset at the same position in `assets`.
#[derive(Debug)]
pub struct Dataset {
    /// Asset ticker symbols in the same order as the return matrix columns.
    pub assets: Vec<String>,

    /// Unix timestamps associated with each return observation.
    pub timestamps: Vec<i64>,

    /// Historical simple returns, with observations as rows and assets as columns.
    pub returns: ndarray::Array2<f64>,
}

impl Dataset {
    /// Creates a new dataset from the provided assets, timestamps, and returns.
    ///
    /// # Arguments
    ///
    /// * `assets` - Ordered list of asset ticker symbols.
    /// * `timestamps` - Timestamps associated with each return observation.
    /// * `returns` - Two-dimensional matrix of historical returns.
    pub fn new(assets: Vec<String>, timestamps: Vec<i64>, returns: ndarray::Array2<f64>) -> Self {
        Dataset {
            assets,
            timestamps,
            returns,
        }
    }

    /// Calculates the minimum and maximum mean returns among the available assets.
    ///
    /// The mean return is calculated independently for each asset by averaging
    /// its historical observations. The resulting bounds correspond to the
    /// lowest and highest individual asset mean returns.
    ///
    /// # Returns
    ///
    /// A tuple containing:
    /// - The minimum mean return among all assets.
    /// - The maximum mean return among all assets.
    ///
    /// # Errors
    ///
    /// Returns an error if the dataset does not contain valid observations
    /// or assets.

    pub fn target_return_bounds(&self) -> Result<(f64, f64)> {
        // TODO: Replace unwrap calls with explicit error handling
        // for empty datasets and invalid return values.
        let mean_returns = self.returns.mean_axis(Axis(0)).unwrap();
        let min_ret = mean_returns
            .iter()
            .copied()
            .min_by(|a, b| a.total_cmp(b))
            .unwrap();
        let max_ret = mean_returns
            .iter()
            .copied()
            .max_by(|a, b| a.total_cmp(b))
            .unwrap();

        Ok((min_ret, max_ret))
    }
}
