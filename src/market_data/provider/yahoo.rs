//! Yahoo Finance market data provider.
//!
//! This module provides asynchronous access to historical market data
//! through the Yahoo Finance API. It retrieves historical quotes and
//! asset metadata, converting the response into the application's
//! internal [`AssetModel`] representation.

// TODO: Verify whether the historical date range is inclusive or exclusive.
// NOTE: The current implementation aborts the entire operation if any
// ticker fails to download.

use time::OffsetDateTime;
use yahoo_finance_api::{self as yahoo};

use crate::domain::AssetModel;
use anyhow::{Context, Result};

/// Downloads historical market data for the specified ticker symbols.
///
/// For each ticker, this function retrieves historical quote data and
/// asset metadata from Yahoo Finance, then converts the response into
/// an [`AssetModel`].
///
/// # Arguments
///
/// * `start` - Beginning of the historical data range.
/// * `end` - End of the historical data range.
/// * `tickers` - List of ticker symbols to retrieve.
///
/// # Returns
///
/// A vector containing one [`AssetModel`] per successfully processed
/// ticker.
///
/// # Errors
///
/// Returns an error if the Yahoo Finance provider cannot be initialized,
/// or if retrieving the historical quotes or metadata for any ticker
/// fails.
pub async fn download(
    start: OffsetDateTime,
    end: OffsetDateTime,
    tickers: &[String],
) -> Result<Vec<AssetModel>> {
    let provider = yahoo::YahooConnector::new().context("Unable to initialize Yahoo Finance")?;
    let mut data_assets = Vec::with_capacity(tickers.len());

    for ticker in tickers {
        let res = provider
            .get_quote_history(ticker, start, end)
            .await
            .context(format!("Unable to download data from {ticker}"))?;

        let metadata = res
            .metadata()
            .context(format!("Unable to retrieve metadata from {ticker}"))?;

        let name = metadata
            .short_name
            .unwrap_or_else(|| metadata.symbol.clone());

        data_assets.push(AssetModel::new(
            metadata.symbol,
            name,
            res.quotes()
                .context(format!("Unable to get quotes from {ticker}"))?,
        ))
    }

    Ok(data_assets)
}
