import yfinance as yf
import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

ticker = yf.Ticker("AAPL", session=session)
df = ticker.history(start="2024-01-01", end="2024-01-10")
print(df)
