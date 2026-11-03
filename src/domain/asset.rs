use crate::domain::types::Quotes;

/// Este modelo representara los datos del activo
/// mas aparte quotes de un rango definido al hacer
/// el query de descarga
///

#[derive(Debug)]
pub struct AssetModel {
    pub symbol: String,
    pub name: String,
    pub quotes: Quotes,
}

impl AssetModel {
    pub fn new(symbol: String, name: String, quotes: Quotes) -> AssetModel {
        AssetModel {
            symbol,
            name,
            quotes,
        }
    }
}

#[derive(Debug)]
pub struct Dataset {
    pub assets: Vec<String>,
    pub timestamps: Vec<i64>,
    pub returns: ndarray::Array2<f64>,
}

impl Dataset {
    pub fn new(assets: Vec<String>, timestamps: Vec<i64>, returns: ndarray::Array2<f64>) -> Self {
        Dataset {
            assets,
            timestamps,
            returns,
        }
    }
}
