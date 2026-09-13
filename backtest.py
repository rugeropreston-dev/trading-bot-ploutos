"""
backtest.py
-----------
New: --trend-filter flag makes the bot sit out strongly trending markets.
"""

import argparse
import pandas as pd
from strategies import STRATEGY_REGISTRY
from risk_management import position_size, atr, atr_stop_loss, take_profit
from trend_filter import apply_trend_filter, regime_summary


def run_backtest(csv_path, strategy_name, starting_balance=1000.0, risk_pct=1.0, fee_pct=0.1,
                  trend_filter=False, trend_lookback=2000, trend_threshold_pct=15.0):
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    strategy_fn = STRATEGY_REGISTRY[strategy_name]
    df = strategy_fn(df)
    df["atr"] = atr(df)

    if trend_filter:
        df = apply_trend_filter(df, lookback=trend_lookback, threshold_pct=trend_threshold_pct)
        summary = regime_summary(df, lookback=trend_lookback, threshold_pct=trend_threshold_pct)
        print("Regime breakdown: " + str(summary))
        print("(Trading only during 'choppy' periods, sitting out uptrend/downtrend)")

    balance = starting_balance
    position = None
    trade_log = []

    for i, row in df.iterrows():
        price = row["close"]

        if position:
            hit_stop = (position["direction"] == "long" and price <= position["stop"]) or \
                       (position["direction"] == "short" and price >= position["stop"])
            hit_target = (position["direction"] == "long" and price >= position["target"]) or \
                         (position["direction"] == "short" and price <= position["target"])

            if hit_stop or hit_target:
                exit_price = position["stop"] if hit_stop else position["target"]
                pnl = (exit_price - position["entry"]) * position["size"] if position["direction"] == "long" \
                    else (position["entry"] - exit_price) * position["size"]
                fee = abs(exit_price * position["size"]) * (fee_pct / 100)
                balance += pnl - fee
                trade_log.append({
                    "date": row["date"], "direction": position["direction"],
                    "entry": position["entry"], "exit": exit_price,
                    "pnl": round(pnl - fee, 2), "balance": round(balance, 2)
                })
                position = None

        if not position and row["signal"] != 0 and not pd.isna(row.get("atr", None)):
            direction = "long" if row["signal"] == 1 else "short"
            stop = atr_stop_loss(price, row["atr"], direction=direction)
            target = take_profit(price, stop, reward_risk_ratio=1.5, direction=direction)
            size = position_size(balance, risk_pct, price, stop)
            if size > 0:
                position = {"entry": price, "stop": stop, "target": target,
                            "size": size, "direction": direction}

    trades_df = pd.DataFrame(trade_log)
    total_trades = len(trades_df)
    wins = (trades_df["pnl"] > 0).sum() if total_trades else 0
    win_rate = (wins / total_trades * 100) if total_trades else 0
    net_return_pct = ((balance - starting_balance) / starting_balance) * 100

    tag = " (trend-filtered)" if trend_filter else ""
    print("")
    print("--- Backtest results: " + strategy_name + tag + " ---")
    print("Starting balance : $" + format(starting_balance, ",.2f"))
    print("Ending balance   : $" + format(balance, ",.2f"))
    print("Net return       : " + format(net_return_pct, ".2f") + "%")
    print("Total trades     : " + str(total_trades))
    print("Win rate         : " + format(win_rate, ".1f") + "%")
    if total_trades:
        print(trades_df.tail(10).to_string(index=False))

    return trades_df, balance


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--strategy", required=True, choices=list(STRATEGY_REGISTRY.keys()))
    parser.add_argument("--balance", type=float, default=1000.0)
    parser.add_argument("--risk", type=float, default=1.0)
    parser.add_argument("--fee", type=float, default=0.1)
    parser.add_argument("--trend-filter", action="store_true")
    parser.add_argument("--trend-lookback", type=int, default=2000)
    parser.add_argument("--trend-threshold", type=float, default=15.0)
    args = parser.parse_args()

    run_backtest(args.csv, args.strategy, args.balance, args.risk, args.fee,
                 args.trend_filter, args.trend_lookback, args.trend_threshold)