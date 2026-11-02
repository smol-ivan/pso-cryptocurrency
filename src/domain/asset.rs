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
