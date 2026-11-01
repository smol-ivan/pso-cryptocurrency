use time::{OffsetDateTime, macros::datetime};
use yahoo_finance_api::{self as yahoo, YResponse};

pub async fn download(
    start: OffsetDateTime,
    end: OffsetDateTime,
    tickers: &[String],
) -> Result<Vec<YResponse>, Box<dyn std::error::Error>> {
    let provider = yahoo::YahooConnector::new().unwrap();
    let mut data_assets = Vec::with_capacity(tickers.len());

    //TODO: as of now the implementation is not concurrent
    // meaning that we dowload one asset and wait to the response
    for ticker in tickers {
        let res = provider.get_quote_history(ticker, start, end).await?;

        data_assets.push(res);
    }

    Ok(data_assets)
}
