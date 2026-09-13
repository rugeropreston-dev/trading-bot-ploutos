"""
alert_if_ready.py
-------------------
Reads auto_test_log.csv and checks for something genuinely worth paying
attention to — NOT just "beat buy-and-hold today" (we proved that means
nothing on its own with the USD/JPY spike that didn't repeat over 2 years).

Bar: a strategy must beat buy-and-hold in 10+ consecutive daily runs,
each with 15+ trades. Only then does it send a Telegram alert.
"""

import pandas as pd
from telegram_notifier import send_message

LOG_PATH = "auto_test_log.csv"
MIN_CONSECUTIVE_WINS = 10
MIN_TRADES_PER_RUN = 15


def check_for_real_signal():
    try:
        df = pd.read_csv(LOG_PATH)
    except FileNotFoundError:
        print(f"{LOG_PATH} doesn't exist yet — run auto_tester.py first.")
        return

    df = df.sort_values(["symbol", "strategy", "run_date"])
    qualifying = []

    for (symbol, strategy), group in df.groupby(["symbol", "strategy"]):
        group = group.sort_values("run_date")
        streak = 0
        for _, row in group[::-1].iterrows():
            if row["beat_buy_and_hold"] and row["trades"] >= MIN_TRADES_PER_RUN:
                streak += 1
            else:
                break

        if streak >= MIN_CONSECUTIVE_WINS:
            avg_return = group.tail(streak)["return_pct"].mean()
            qualifying.append({
                "symbol": symbol, "strategy": strategy,
                "consecutive_wins": streak, "avg_return_pct": round(avg_return, 2)
            })

    if qualifying:
        print(f"\n*** {len(qualifying)} strategy/symbol combo(s) meet the real-signal bar ***")
        message_lines = ["Ploutos alert: possible real edge detected\n"]
        for q in qualifying:
            line = (f"{q['strategy']} on {q['symbol']}: beat buy-and-hold "
                    f"{q['consecutive_wins']} runs in a row, avg return {q['avg_return_pct']}%")
            print(line)
            message_lines.append(line)
        message_lines.append(
            "\nThis passed a real bar (10+ consecutive wins, 15+ trades each) — "
            "still verify with out-of-sample testing before trusting it with money."
        )
        send_message("\n".join(message_lines))
    else:
        print("No strategy/symbol combo has met the real-signal bar yet "
              f"(needs {MIN_CONSECUTIVE_WINS}+ consecutive daily wins with "
              f"{MIN_TRADES_PER_RUN}+ trades each). Keep running auto_tester.py daily.")


if __name__ == "__main__":
    check_for_real_signal()