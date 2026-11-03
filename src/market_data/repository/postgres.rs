//! PostgreSQL repository for market data persistence.
//!
//! This module provides database operations for storing historical
//! market prices. It uses SQLx and PostgreSQL transactions to ensure
//! atomic persistence of asset quotes.

// TODO: Evaluate whether processing all assets within a single transaction
// is appropriate for large historical datasets.
use anyhow::Result;
use sqlx::PgPool;

use crate::domain::AssetModel;

/// Persists historical market data for the provided assets.
///
/// Each quote is inserted into the `market_prices` table. If a record
/// with the same symbol and timestamp already exists, its price and
/// volume fields are updated instead.
///
/// All database operations are executed within a single transaction.
/// Changes are committed only if every quote is processed successfully.
///
/// # Arguments
///
/// * `pool` - PostgreSQL connection pool.
/// * `assets` - Assets containing the historical quotes to persist.
///
/// # Errors
///
/// Returns an error if:
/// - A database transaction cannot be started.
/// - A quote volume cannot be converted to `i64`.
/// - Any database insertion or update fails.
/// - The transaction cannot be committed.
pub async fn save_assets(pool: &PgPool, assets: &[AssetModel]) -> Result<()> {
    let mut tx = pool.begin().await?;

    for asset in assets {
        for quote in &asset.quotes {
            let volume = i64::try_from(quote.volume)?;

            sqlx::query(
                r#"
                INSERT INTO market_prices (
                    symbol,
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    adjclose,
                    volume
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)

                ON CONFLICT (symbol, timestamp)
                DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    adjclose = EXCLUDED.adjclose,
                    volume = EXCLUDED.volume
            "#,
            )
            .bind(&asset.symbol)
            .bind(quote.timestamp)
            .bind(quote.open)
            .bind(quote.high)
            .bind(quote.low)
            .bind(quote.close)
            .bind(quote.adjclose)
            .bind(volume)
            .execute(&mut *tx)
            .await?;
        }
    }

    tx.commit().await?;

    Ok(())
}
