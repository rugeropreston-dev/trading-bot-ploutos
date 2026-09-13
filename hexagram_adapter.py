"""
hexagram_adapter.py
--------------------
Bridges hexagram_model/ into the main bot's strategies.py registry, so you
can backtest it with the exact same backtest.py used for the simple
strategies:

    python backtest.py --csv data/your_real_data.csv --strategy hexagram

IMPORTANT: This strategy needs to FIT the forward-return table on a training
slice of data before it can generate signals on a test slice. Using it via
the registry auto-fits on the first 70% of whatever CSV you pass in, then
generates signals on the full series — that's fine for a quick check, but
for a real evaluation you should keep a proper train/test split yourself
(see hexagram_model/hexagram_strategy.py directly for full control).

No news headlines are used in this registry hookup (backtest.py has no
historical headline data) — this tests the TECHNICAL half only. To use the
full sentiment-adjusted version, call hexagram_strategy.py functions
directly with real headlines for your symbol.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "hexagram_model"))

from hexagram_encoder import encode_hexagram
from markov_model import build_forward_return_table, hexagram_signal


def hexagram_strategy_for_registry(df: pd.DataFrame, train_fraction: float = 0.7,
                                    forward_bars: int = 5, min_samples: int = 20) -> pd.DataFrame:
    df = df.copy()
    split = int(len(df) * train_fraction)
    train_df = df.iloc[:split].reset_index(drop=True)
    train_df = encode_hexagram(train_df)
    table = build_forward_return_table(train_df, forward_bars=forward_bars, min_samples=min_samples)

    full_df = hexagram_signal(df, table)
    # Zero out signals during the training window — those bars were used to
    # BUILD the model and trading on them would be misleadingly circular
    full_df.loc[:split, "signal"] = 0
    return full_df
