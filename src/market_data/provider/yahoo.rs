use time::OffsetDateTime;
use yahoo_finance_api::{self as yahoo};

use crate::domain::AssetModel;

pub async fn download(
    start: OffsetDateTime,
    end: OffsetDateTime,
    tickers: &[String],
) -> Result<Vec<AssetModel>, Box<dyn std::error::Error>> {
    let provider = yahoo::YahooConnector::new().unwrap();
    let mut data_assets = Vec::with_capacity(tickers.len());

    for ticker in tickers {
        let res = provider.get_quote_history(ticker, start, end).await?;

        data_assets.push(AssetModel::new(
            res.metadata()?.symbol,
            res.metadata()?.short_name.unwrap(),
            res.quotes()?,
        ))
    }

    Ok(data_assets)
}
