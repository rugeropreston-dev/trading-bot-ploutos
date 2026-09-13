"""
compare_on_csv.py
-------------------
Works on ANY existing CSV file directly — no broker connection needed.
Tests forex data (or anything else) the same way we tested AAPL/SPY/BTC/TSLA.
Runs all 5 basic strategies AND trend-following, plus buy-and-hold.

Usage:
    python compare_on_csv.py --csv data/EURUSD_X_1h.csv
"""

import argparse
import pandas as pd
from strategies import STRATEGY_REGISTRY
from backtest import run_backtest
from trend_following import run_trend_following_backtest


def buy_and_hold_return(csv_path):
    df = pd.read_csv(csv_path)
    return (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100


def run_comparison(csv_path, starting_balance=1000.0, risk_pct=1.0,
                    tf_entry_period=55, tf_exit_atr_mult=3.0):
    results = []

    for name in STRATEGY_REGISTRY:
        try:
            trades_df, ending_balance = run_backtest(
                csv_path, name, starting_balance=starting_balance, risk_pct=risk_pct
            )
            net_return = (ending_balance - starting_balance) / starting_balance * 100
            total_trades = len(trades_df)
            win_rate = (trades_df["pnl"] > 0).mean() * 100 if total_trades else 0
            results.append({"strategy": name, "return_pct": round(net_return, 2),
                             "win_rate_pct": round(win_rate, 1), "trades": total_trades})
        except Exception as e:
            results.append({"strategy": name, "return_pct": None, "win_rate_pct": None,
                             "trades": None, "error": str(e)})

    try:
        tf_trades, tf_balance = run_trend_following_backtest(
            csv_path, entry_period=tf_entry_period, exit_atr_mult=tf_exit_atr_mult,
            starting_balance=starting_balance, risk_pct=risk_pct
        )
        tf_return = (tf_balance - starting_balance) / starting_balance * 100
        tf_total = len(tf_trades)
        tf_win_rate = (tf_trades["pnl"] > 0).mean() * 100 if tf_total else 0
        results.append({"strategy": "trend_following", "return_pct": round(tf_return, 2),
                         "win_rate_pct": round(tf_win_rate, 1), "trades": tf_total})
    except Exception as e:
        results.append({"strategy": "trend_following", "return_pct": None,
                         "win_rate_pct": None, "trades": None, "error": str(e)})

    bh_return = buy_and_hold_return(csv_path)
    results.append({"strategy": "buy_and_hold", "return_pct": round(bh_return, 2),
                     "win_rate_pct": "-", "trades": "-"})

    results_df = pd.DataFrame(results).sort_values("return_pct", ascending=False, na_position="last")

    print("")
    print("============================================================")
    print("  STRATEGY COMPARISON: " + csv_path)
    print("============================================================")
    print(results_df.to_string(index=False))
    print("============================================================")

    beat_bh = results_df[(results_df["strategy"] != "buy_and_hold") & (results_df["return_pct"] > bh_return)]
    if len(beat_bh) == 0:
        print("")
        print("No strategy beat buy-and-hold (" + str(round(bh_return, 2)) + "%) on this data.")
    else:
        print("")
        print("Strategies that beat buy-and-hold (" + str(round(bh_return, 2)) + "%):")
        print(beat_bh[["strategy", "return_pct"]].to_string(index=False))

    return results_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--balance", type=float, default=1000.0)
    parser.add_argument("--risk", type=float, default=1.0)
    parser.add_argument("--tf-entry-period", type=int, default=55)
    parser.add_argument("--tf-exit-atr-mult", type=float, default=3.0)
    args = parser.parse_args()

    run_comparison(args.csv, args.balance, args.risk, args.tf_entry_period, args.tf_exit_atr_mult)