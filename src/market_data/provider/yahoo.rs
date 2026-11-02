use time::OffsetDateTime;
use yahoo_finance_api::{self as yahoo};

use crate::domain::AssetModel;

// For this specific fn, we have different type or errors
// error to connect to yahoo
// error via http petition
// error to get metadata
// error to get quotes

// because of that we use dyn error, so we can cover every type
// with anyhow can be use as an alias as anyhow can store different
// errors
use anyhow::{Context, Result};

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
