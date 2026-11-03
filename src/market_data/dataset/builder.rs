use sqlx::Row;
use std::collections::{BTreeMap, HashMap};

use anyhow::{Context, Result, bail, ensure};
use ndarray::Array2;
use sqlx::PgPool;
use time::OffsetDateTime;

use crate::domain::Dataset;

/// Consult, validate, align and transform data from data_market table.
///
/// $$R_{i,t} = P_{i,t} / P_{i,t-1} − 1$$
///
/// Where:
/// - $P_{i,t}$: asset price $i$ in period $t$.
/// - $P_{i,t-1}$: asset price in the previous period.
pub async fn build(
    pool: &PgPool,
    assets: &[String],
    start: OffsetDateTime,
    end: OffsetDateTime,
) -> Result<Dataset> {
    // Validacion de parametros
    ensure!(!assets.is_empty(), "Should specify at least one asset");

    ensure!(start < end, "Start date should be after the end date");

    // TODO: should validate empty strings and duplicates

    let symbols = assets.to_vec();

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

    // TODO: Validate that results is non empty

    let mut prices_by_timestamp: BTreeMap<i64, HashMap<String, f64>> = BTreeMap::new();

    for row in rows {
        let timestamp: i64 = row.try_get("timestamp")?;
        let symbol: String = row.try_get("symbol")?;
        let close: f64 = row.try_get("close")?;

        // TODO: Validate that close is valid: ex above 0 or non infinite

        prices_by_timestamp
            .entry(timestamp)
            .or_default()
            .insert(symbol, close);
    }

    // Construction of matrix price orderer by asset and date
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

    // TODO: validate daily continuity

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
