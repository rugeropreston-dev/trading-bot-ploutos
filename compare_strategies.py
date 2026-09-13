"""
compare_strategies.py
----------------------
Runs every strategy against a symbol, plus buy-and-hold. Add --trend-filter
to test the trend-aware version.
"""

import os
import argparse
import pandas as pd
from data_fetcher import fetch_stock_bars, fetch_crypto_bars
from backtest import run_backtest
from strategies import STRATEGY_REGISTRY


def get_data(symbol, timeframe, days, crypto, refresh):
    out_path = f"data/{symbol.replace('/', '_')}_{timeframe}.csv"
    if os.path.exists(out_path) and not refresh:
        print(f"Using cached data: {out_path} (pass --refresh to re-pull)")
        return out_path

    print(f"Fetching {days} days of {timeframe} bars for {symbol}...")
    fetch_fn = fetch_crypto_bars if crypto else fetch_stock_bars
    df = fetch_fn(symbol, timeframe, days)
    os.makedirs("data", exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} bars to {out_path}")
    return out_path


def buy_and_hold_return(csv_path):
    df = pd.read_csv(csv_path)
    return (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100


def run_comparison(symbol, timeframe="1Hour", days=365, crypto=False, refresh=False,
                    starting_balance=1000.0, risk_pct=1.0,
                    trend_filter=False, trend_lookback=2000, trend_threshold=15.0):
    csv_path = get_data(symbol, timeframe, days, crypto, refresh)

    results = []
    for name in STRATEGY_REGISTRY:
        try:
            trades_df, ending_balance = run_backtest(
                csv_path, name, starting_balance=starting_balance, risk_pct=risk_pct,
                trend_filter=trend_filter, trend_lookback=trend_lookback,
                trend_threshold_pct=trend_threshold
            )
            net_return = (ending_balance - starting_balance) / starting_balance * 100
            total_trades = len(trades_df)
            win_rate = (trades_df["pnl"] > 0).mean() * 100 if total_trades else 0
            results.append({"strategy": name, "return_pct": round(net_return, 2),
                             "win_rate_pct": round(win_rate, 1), "trades": total_trades})
        except Exception as e:
            results.append({"strategy": name, "return_pct": None, "win_rate_pct": None,
                             "trades": None, "error": str(e)})

    bh_return = buy_and_hold_return(csv_path)
    results.append({"strategy": "buy_and_hold", "return_pct": round(bh_return, 2),
                     "win_rate_pct": "-", "trades": "-"})

    results_df = pd.DataFrame(results).sort_values("return_pct", ascending=False, na_position="last")

    label = " (TREND-FILTERED)" if trend_filter else ""
    print("")
    print("============================================================")
    print("  STRATEGY COMPARISON: " + symbol + label + "  (" + str(days) + " days, " + timeframe + ")")
    print("============================================================")
    print(results_df.to_string(index=False))
    print("============================================================")

    beat_bh = results_df[(results_df["strategy"] != "buy_and_hold") & (results_df["return_pct"] > bh_return)]
    if len(beat_bh) == 0:
        print("")
        print("No strategy beat buy-and-hold (" + str(round(bh_return, 2)) + "%) on this symbol/period.")
    else:
        print("")
        print("Strategies that beat buy-and-hold (" + str(round(bh_return, 2)) + "%):")
        print(beat_bh[["strategy", "return_pct"]].to_string(index=False))

    return results_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1Hour")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--crypto", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--balance", type=float, default=1000.0)
    parser.add_argument("--risk", type=float, default=1.0)
    parser.add_argument("--trend-filter", action="store_true")
    parser.add_argument("--trend-lookback", type=int, default=2000)
    parser.add_argument("--trend-threshold", type=float, default=15.0)
    args = parser.parse_args()

    run_comparison(args.symbol, args.timeframe, args.days, args.crypto, args.refresh,
                    args.balance, args.risk, args.trend_filter, args.trend_lookback,
                    args.trend_threshold)