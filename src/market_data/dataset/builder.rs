//! Historical market data retrieval and dataset construction.
//!
//! This module retrieves historical asset prices from PostgreSQL,
//! validates and aligns observations across the requested assets,
//! and transforms prices into simple returns.
//!
//! The resulting dataset contains a two-dimensional return matrix,
//! where rows represent observation periods and columns represent
//! assets in the same order as the input asset list.
use sqlx::Row;
use std::collections::{BTreeMap, HashMap};

use anyhow::{Context, Result, bail, ensure};
use ndarray::Array2;
use sqlx::PgPool;
use time::OffsetDateTime;

use crate::domain::Dataset;

/// Builds a dataset of historical asset returns from stored market prices.
///
/// This function retrieves closing prices for the requested assets within
/// the specified date range. Only timestamps shared by all requested
/// assets are retained, ensuring temporal alignment across price series.
///
/// Prices are organized into a matrix and transformed into simple
/// period returns using:
///
/// $$R_{i,t} = \frac{P_{i,t}}{P_{i,t-1}} - 1$$
///
/// Where:
/// - $R_{i,t}$ represents the return of asset $i$ at period $t$.
/// - $P_{i,t}$ represents the closing price of asset $i$ at period $t$.
/// - $P_{i,t-1}$ represents the previous closing price of asset $i$.
///
/// # Arguments
///
/// * `pool` - PostgreSQL connection pool.
/// * `assets` - Ordered list of asset ticker symbols to include.
/// * `start` - Beginning of the historical data range.
/// * `end` - End of the historical data range.
///
/// # Returns
///
/// A [`Dataset`] containing:
/// - The requested asset symbols in their original order.
/// - Timestamps associated with the calculated return observations.
/// - A two-dimensional matrix of simple returns, with observations
///   as rows and assets as columns.
///
/// # Errors
///
/// Returns an error if:
/// - No assets are provided.
/// - The start date is not earlier than the end date.
/// - The database query fails.
/// - Retrieved rows cannot be decoded.
/// - An asset price is missing for an expected timestamp.
/// - The return matrix cannot be constructed.
pub async fn build(
    pool: &PgPool,
    assets: &[String],
    start: OffsetDateTime,
    end: OffsetDateTime,
) -> Result<Dataset> {
    // Validacion de parametros
    ensure!(!assets.is_empty(), "Should specify at least one asset");

    ensure!(start < end, "Start date must be earlier than end date");

    // TODO: should validate empty strings and duplicates

    let symbols = assets.to_vec();

    // Retrieve closing prices for the requested assets within the specified
    // date range.
    //
    // The `common_dates` CTE identifies timestamps where all requested assets
    // have available price records. This ensures that every observation
    // contains data for the complete asset set.
    //
    // The main query retrieves the corresponding closing prices and orders
    // them chronologically, grouping assets by timestamp.
    let rows = sqlx::query(
        r#"
        WITH common_dates AS (
            SELECT timestamp
            FROM market_prices
            WHERE symbol = ANY($1::text[])
              AND timestamp >= $2
              AND timestamp <= $3
            GROUP BY timestamp
            HAVING COUNT(DISTINCT symbol) = cardinality($1::text[])
        )

        SELECT
            mp.timestamp,
            mp.symbol,
            mp.close::DOUBLE PRECISION AS close
        FROM market_prices mp
        INNER JOIN common_dates cd
            ON mp.timestamp = cd.timestamp
        WHERE mp.symbol = ANY($1::text[])
        ORDER BY mp.timestamp, mp.symbol
        "#,
    )
    .bind(&symbols)
    .bind(start.unix_timestamp())
    .bind(end.unix_timestamp())
    .fetch_all(pool)
    .await
    .context("Error trying to fetch data")?;

    // TODO: Validate that asset symbols are non-empty and unique.
    // TODO: Validate that the query returns at least two observations
    // before calculating returns.

    // Group prices by timestamp to ensure chronological ordering
    // and facilitate alignment across the requested assets.

    let mut prices_by_timestamp: BTreeMap<i64, HashMap<String, f64>> = BTreeMap::new();

    for row in rows {
        let timestamp: i64 = row.try_get("timestamp")?;
        let symbol: String = row.try_get("symbol")?;
        let close: f64 = row.try_get("close")?;

        // TODO: Validate that closing prices are finite and strictly positive.

        prices_by_timestamp
            .entry(timestamp)
            .or_default()
            .insert(symbol, close);
    }

    // Build the price matrix while preserving the original asset order.
    let mut timestamps = Vec::with_capacity(prices_by_timestamp.len());
    let mut prices = Vec::with_capacity(prices_by_timestamp.len() * assets.len());

    for (timestamp, asset_prices) in &prices_by_timestamp {
        timestamps.push(*timestamp);

        for asset in assets {
            let price = asset_prices.get(asset).with_context(|| {
                format!("Asset {asset} price not found for timestamp {timestamp}")
            })?;
            prices.push(*price);
        }
    }

    // TODO: Validate continuity between consecutive observations
    // if daily returns are required.
    // Calculate simple return

    let n_observations = timestamps.len();
    let n_assets = assets.len();

    let mut returns = Vec::with_capacity((n_observations - 1) * n_assets);

    for t in 1..n_observations {
        for asset_idx in 0..n_assets {
            let previous_price = prices[(t - 1) * n_assets + asset_idx];

            let current_price = prices[t * n_assets + asset_idx];

            let daily_return = current_price / previous_price - 1.0;

            returns.push(daily_return);
        }
    }

    // ndarray Construction

    let returns = Array2::from_shape_vec((n_observations - 1, n_assets), returns)?;

    let return_timestamps = timestamps.into_iter().skip(1).collect();

    let dataset = Dataset::new(assets.to_vec(), return_timestamps, returns);

    Ok(dataset)
}
