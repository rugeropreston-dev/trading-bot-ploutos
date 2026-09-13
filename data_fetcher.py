
import os
import argparse
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ALPACA_API_KEY", "")
SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")

HEADERS = {
    "APCA-API-KEY-ID": API_KEY,
    "APCA-API-SECRET-KEY": SECRET_KEY,
}

def fetch_stock_bars(symbol: str, timeframe: str = "1Hour", days: int = 60) -> pd.DataFrame:
    """Fetch historical stock bars (e.g. AAPL, TSLA) via Alpaca's data API.
    Handles pagination — Alpaca returns results in pages via next_page_token,
    so a single request often only returns a small slice of a large date range."""
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    params = {"timeframe": timeframe, "start": start, "limit": 10000, "adjustment": "raw"}

    all_bars = []
    page_token = None
    while True:
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(url, headers=HEADERS, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        all_bars.extend(data.get("bars", []))
        page_token = data.get("next_page_token")
        if not page_token:
            break

    df = pd.DataFrame(all_bars)
    df = df.rename(columns={"t": "date", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return df[["date", "open", "high", "low", "close", "volume"]]



def fetch_crypto_bars(symbol, timeframe="1Hour", days=60):
    """Fetch historical crypto bars (e.g. BTC/USD) via Alpaca's crypto data API.
    Handles pagination the same way as fetch_stock_bars."""
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = "https://data.alpaca.markets/v1beta3/crypto/us/bars"
    params = {"symbols": symbol, "timeframe": timeframe, "start": start, "limit": 10000}

    all_bars = []
    page_token = None
    while True:
        if page_token:
            params["page_token"] = page_token
        resp = requests.get(url, headers=HEADERS, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        all_bars.extend(data.get("bars", {}).get(symbol, []))
        page_token = data.get("next_page_token")
        if not page_token:
            break

    df = pd.DataFrame(all_bars)
    df = df.rename(columns={"t": "date", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return df[["date", "open", "high", "low", "close", "volume"]]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1Hour")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--crypto", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if not API_KEY or not SECRET_KEY:
        raise SystemExit("Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your environment first.")

    fetch_fn = fetch_crypto_bars if args.crypto else fetch_stock_bars
    df = fetch_fn(args.symbol, args.timeframe, args.days)

    out_path = args.out or f"data/{args.symbol.replace('/', '_')}_{args.timeframe}.csv"
    os.makedirs("data", exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} bars to {out_path}")
