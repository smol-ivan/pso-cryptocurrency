use anyhow::Result;
use sqlx::PgPool;

use crate::domain::AssetModel;

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
