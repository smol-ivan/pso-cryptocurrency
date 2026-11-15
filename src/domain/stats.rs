use anyhow::{Result, ensure};
use serde::Serialize;

use super::Dataset;

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct TargetReturnBounds {
    pub min: f64,
    pub max: f64,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct DatasetStats {
    pub assets: Vec<String>,
    pub n_observations: usize,
    pub first_timestamp: i64,
    pub last_timestamp: i64,
    pub mean_returns: Vec<f64>,
    pub std_returns: Vec<f64>,
    pub covariance: Vec<Vec<f64>>,
    pub return_type: String,
    pub periods_per_year: f64,
    pub target_return_bounds: TargetReturnBounds,
}

impl DatasetStats {
    pub fn from_dataset(dataset: &Dataset, periods_per_year: f64) -> Result<Self> {
        let n_observations = dataset.returns.nrows();
        let n_assets = dataset.returns.ncols();
        ensure!(
            n_observations >= 2,
            "dataset must contain at least 2 observations"
        );
        ensure!(
            dataset.timestamps.len() == n_observations,
            "dataset timestamps must match the number of observations"
        );
        ensure!(
            dataset.assets.len() == n_assets,
            "dataset assets must match the number of return columns"
        );
        ensure!(
            periods_per_year.is_finite() && periods_per_year > 0.0,
            "periods_per_year must be finite and greater than zero"
        );
        ensure!(
            dataset.returns.iter().all(|value| value.is_finite()),
            "dataset returns must be finite"
        );

        let n = n_observations as f64;
        let mean_returns: Vec<f64> = (0..n_assets)
            .map(|column| dataset.returns.column(column).sum() / n)
            .collect();
        let std_returns: Vec<f64> = (0..n_assets)
            .map(|column| {
                let variance = dataset
                    .returns
                    .column(column)
                    .iter()
                    .map(|value| (value - mean_returns[column]).powi(2))
                    .sum::<f64>()
                    / n;
                variance.sqrt()
            })
            .collect();
        let covariance: Vec<Vec<f64>> = (0..n_assets)
            .map(|left| {
                (0..n_assets)
                    .map(|right| {
                        dataset
                            .returns
                            .rows()
                            .into_iter()
                            .map(|row| {
                                (row[left] - mean_returns[left])
                                    * (row[right] - mean_returns[right])
                            })
                            .sum::<f64>()
                            / n
                    })
                    .collect()
            })
            .collect();
        let min = mean_returns.iter().copied().fold(f64::INFINITY, f64::min);
        let max = mean_returns
            .iter()
            .copied()
            .fold(f64::NEG_INFINITY, f64::max);

        Ok(Self {
            assets: dataset.assets.clone(),
            n_observations,
            first_timestamp: dataset.timestamps[0],
            last_timestamp: dataset.timestamps[n_observations - 1],
            mean_returns,
            std_returns,
            covariance,
            return_type: "simple".to_owned(),
            periods_per_year,
            target_return_bounds: TargetReturnBounds { min, max },
        })
    }
}

#[cfg(test)]
mod tests {
    use ndarray::array;

    use super::*;

    #[test]
    fn computes_population_statistics() {
        let dataset = Dataset::new(
            vec!["BTC".into(), "ETH".into()],
            vec![100, 200, 300],
            array![[1.0, 2.0], [3.0, 4.0], [5.0, 8.0]],
        );

        let stats = DatasetStats::from_dataset(&dataset, 365.0).unwrap();

        assert_eq!(stats.assets, ["BTC", "ETH"]);
        assert_eq!(stats.n_observations, 3);
        assert_eq!(stats.first_timestamp, 100);
        assert_eq!(stats.last_timestamp, 300);
        assert_eq!(stats.mean_returns, [3.0, 14.0 / 3.0]);
        assert!((stats.std_returns[0] - (8.0 / 3.0_f64).sqrt()).abs() < 1e-12);
        assert!((stats.std_returns[1] - (56.0 / 9.0_f64).sqrt()).abs() < 1e-12);
        assert_eq!(stats.covariance[0][0], 8.0 / 3.0);
        assert_eq!(stats.covariance[0][1], 4.0);
        assert_eq!(stats.covariance[1][0], 4.0);
        assert!((stats.covariance[1][1] - 56.0 / 9.0).abs() < 1e-12);
        assert_eq!(stats.return_type, "simple");
        assert_eq!(stats.periods_per_year, 365.0);
        assert_eq!(
            stats.target_return_bounds,
            TargetReturnBounds {
                min: 3.0,
                max: 14.0 / 3.0
            }
        );
    }

    #[test]
    fn requires_two_observations() {
        let dataset = Dataset::new(vec!["BTC".into()], vec![100], array![[1.0]]);
        assert!(DatasetStats::from_dataset(&dataset, 365.0).is_err());
    }
}
