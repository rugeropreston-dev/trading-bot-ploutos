"""
generate_sample_data.py
------------------------
Creates a synthetic OHLCV CSV so you can test backtest.py immediately,
without needing to hook up a live data source first.

For REAL historical data once you're ready:
  - Stocks: export from TradingView chart, or use Alpaca's /v2/stocks/{symbol}/bars endpoint
  - Crypto: use your exchange's API (Binance, Coinbase, etc. all offer free historical candles)

Run: python generate_sample_data.py
"""

import numpy as np
import pandas as pd

np.random.seed(42)
n = 500
dates = pd.date_range("2024-01-01", periods=n, freq="1h")

price = 100
rows = []
for d in dates:
    change = np.random.normal(0, 0.6)
    open_p = price
    close_p = price + change
    high_p = max(open_p, close_p) + abs(np.random.normal(0, 0.3))
    low_p = min(open_p, close_p) - abs(np.random.normal(0, 0.3))
    volume = np.random.randint(1000, 10000)
    rows.append([d, open_p, high_p, low_p, close_p, volume])
    price = close_p

df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
df.to_csv("data/sample.csv", index=False)
print("Wrote data/sample.csv with", len(df), "rows")
