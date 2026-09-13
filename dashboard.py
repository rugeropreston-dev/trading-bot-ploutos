"""
dashboard.py
------------
A tiny live dashboard for the bot. Reads trades.db (written by
webhook_server.py / backtest.py via trade_logger.py) and shows:
  - total trades, win rate, total P&L, latest balance
  - a table of recent trades

Run: python dashboard.py
Then open: http://localhost:5050
"""

from flask import Flask, render_template
from trade_logger import get_all_trades, get_summary

app = Flask(__name__)


@app.route("/")
def index():
    trades = get_all_trades(limit=100)
    summary = get_summary()
    return render_template("dashboard.html", trades=trades, summary=summary)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
