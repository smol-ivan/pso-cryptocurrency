import yfinance as yf

dat = yf.Ticker("USDT-USD")
hist = dat.history(start="2024-01-01", period="2y", interval="1mo")
print(hist)
