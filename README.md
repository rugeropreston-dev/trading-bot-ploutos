[README.md](https://github.com/user-attachments/files/32163167/README.md)
# Preston's Trading Bot — Full Package (v2)

Everything here is tested and runs. This version adds a live dashboard,
Telegram alerts, a real-data fetcher, and the hexagram/Markov + sentiment
model on top of the original strategy bot.

**Not financial advice.** Every strategy in here has lost money in at least
one test. Backtests on synthetic/random data (used to prove the code runs)
prove nothing about real market edge — see the hexagram warning below,
it's important.

## Folder map

```
trading_bot/
├── strategies.py              # 5 basic strategies + hexagram plugged in
├── risk_management.py         # position sizing, ATR stops, daily loss limiter
├── backtest.py                 # test any strategy on historical CSV data
├── generate_sample_data.py     # fake data so backtest.py works immediately
├── data_fetcher.py             # pulls REAL historical bars from Alpaca
├── webhook_server.py           # receives TradingView alerts -> places trades
├── broker_alpaca.py            # order execution via Alpaca paper API
├── trade_logger.py             # SQLite log of every trade
├── dashboard.py + templates/   # live P&L dashboard (localhost:5050)
├── telegram_notifier.py        # phone alerts on every trade
├── hexagram_adapter.py         # plugs hexagram model into backtest.py
├── pine_scripts/*.pine         # TradingView alert scripts
├── hexagram_model/
│   ├── hexagram_encoder.py     # 6 binary signals -> 64 market states
│   ├── markov_model.py         # transition matrix + forward-return table
│   ├── sentiment.py            # lexicon scorer (+ optional FinBERT)
│   ├── news_fetcher.py         # pulls real headlines (Alpaca or NewsAPI)
│   └── hexagram_strategy.py    # combines technical + sentiment signal
├── requirements.txt
└── .env.example
```

## Part 1: Running the basic bot (recap + what's new)

### Quick test (no API keys needed)
```bash
pip install -r requirements.txt
python generate_sample_data.py
python backtest.py --csv data/sample.csv --strategy combo
```

### What's new since last time
1. **Real data**: `python data_fetcher.py --symbol AAPL --days 60` pulls
   actual historical bars from Alpaca instead of fake random data. Do this
   before trusting any backtest number.
2. **Live dashboard**: `python dashboard.py` then open `localhost:5050`.
   Shows total trades, win rate, P&L, and a live-updating trade table.
   Reads from `trades.db`, which `webhook_server.py` now writes to
   automatically.
3. **Telegram alerts**: set `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` in
   `.env` (setup steps are in `telegram_notifier.py`'s docstring), and every
   trade + error gets pushed to your phone. Test with
   `python telegram_notifier.py`.
4. **Circuit breaker wired in**: `webhook_server.py` now checks your account
   equity against a 3%-daily-loss floor before every trade and refuses to
   trade further if it's been breached (from `risk_management.py`,
   which was already there but wasn't connected before).

## Part 2: The hexagram/Markov + sentiment model

### The idea, explained plainly
Take 6 yes/no technical conditions for a given candle (price vs moving
averages, RSI vs 50, MACD vs its signal line, price vs Bollinger midline,
volume vs its average). Stack those 6 bits into one number 0–63 — that's
the "hexagram" for that moment, borrowing the 6-line structure from the
I Ching purely as a label, not for any mystical reason.

Then look at history: every time the market was in hexagram state #42,
what happened next on average? If state #42 was reliably followed by a
+0.8% move, that's a measurable (not mystical) statistical pattern you can
trade. A Markov transition matrix additionally tells you how "sticky" each
state is — does the market tend to stay in state #42, or immediately jump
elsewhere?

News sentiment (scored from real headlines, lexicon-based by default,
upgradable to FinBERT) then acts as a **veto filter**: if the technical
signal says "buy" but the news is strongly bearish, the trade gets skipped
rather than blindly overridden by either signal alone.

### The most important warning in this whole package
64 possible states is a lot of ways to slice your data thin. With a few
thousand historical bars, most states will only occur a handful of times.
A state that looks like it has a "90% win rate" from 3 occurrences is
noise, full stop — not edge. I tested this exact failure mode: on pure
random-walk synthetic data (no real pattern exists by construction), the
model still produced a +19.6% backtest return with a 52.5% win rate. That
number is meaningless — it's overfitting to noise, not a discovered edge.
The `min_samples` filter in `markov_model.py` exists specifically to guard
against this, but it's a blunt instrument. Treat any hexagram result with
deep suspicion until validated on:
- A large amount of REAL data (10,000+ bars minimum, ideally more)
- An out-of-sample test period the model never saw during fitting
- Multiple different market conditions (trending, ranging, volatile, calm)

This is a research tool for exploring whether a pattern-based edge exists
— not something to connect to real money based on a good-looking backtest
number alone.

### Running it
```bash
cd hexagram_model
python hexagram_encoder.py      # sanity-check the encoding logic
python markov_model.py          # sanity-check on synthetic data
python sentiment.py             # test sentiment scoring (lexicon by default)
```

### Fitting on real data + testing via the main backtester
```bash
python data_fetcher.py --symbol AAPL --days 365   # get real data first!
python backtest.py --csv data/AAPL_1Hour.csv --strategy hexagram
```
This uses `hexagram_adapter.py`, which auto-splits your CSV 70/30
(train/test) so the model doesn't just memorize the data it's tested on.
For a real research workflow with proper train/test control and news
sentiment included, use `hexagram_model/hexagram_strategy.py` directly —
see its `if __name__ == "__main__"` block for a full example.

### Upgrading sentiment to FinBERT (optional, better accuracy)
```bash
pip install transformers torch   # ~1-2GB download, needs internet access
```
`sentiment.py` auto-detects and switches to FinBERT once installed — no
code changes needed. Falls back to the lexicon scorer if unavailable.

### Getting real news headlines
```bash
python hexagram_model/news_fetcher.py AAPL
```
Uses Alpaca's news endpoint by default (same keys you already have), falls
back to NewsAPI if you set `NEWSAPI_KEY`.

## What's genuinely still left to do

- **Statistical validation of the hexagram model on real data** — this is
  the big one. Don't skip the warning above.
- **Walk-forward re-fitting** — markets change regime; the forward-return
  table should be refit periodically (weekly/monthly) on a rolling window,
  not fit once and used forever
- **Slippage/fee modeling in the backtester** — still assumes perfect fills
- **Multi-symbol orchestration** — current webhook handles one alert at a
  time; a queue or async worker would help if you scale to many tickers
- **Deployment** — a small always-on VPS (~$5/mo) instead of your laptop,
  so the webhook server and dashboard run 24/7
- **Dashboard auth** — right now `dashboard.py` has zero login protection;
  fine on localhost, needs at least basic auth if you ever expose it
  publicly
