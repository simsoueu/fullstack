import sqlite3

import pandas as pd
import config
import alpaca_trade_api as tradeapi
from datetime import date

# from stockstats import StockDataFrame as Sdf
import pandas_ta as ta

connection = sqlite3.connect(config.DB_FILE)

connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute(
    """
    SELECT id, symbol, company FROM stock
"""
)

rows = cursor.fetchall()

symbols = [row["symbol"] for row in rows]
stock_dict = {}
for row in rows:
    symbol = row["symbol"]
    symbols.append(symbol)
    stock_dict[symbol] = row["id"]

api = tradeapi.REST(config.API_KEY, config.SECRET_KEY, base_url=config.API_URL)

chunk_size = 200
for i in range(0, len(symbols), chunk_size):
    symbol_chunk = symbols[i : i + chunk_size]
    barsets = api.get_barset(symbol_chunk, "day")

    for symbol in barsets:
        # print(f"processing symbol {symbol}")

        recent_closes = [[bar.o, bar.h, bar.l, bar.c] for bar in barsets[symbol]]
        _s = pd.DataFrame(recent_closes)
        close_idx = 3
        rsi, sma_20, sma_50 = None, None, None

        for bar in barsets[symbol]:
            good_date = date.today().isoformat() == bar.t.date().isoformat()
            stock_id = stock_dict[symbol]

            if len(_s) > 14 and good_date:
                rsi = ta.rsi(_s[close_idx], lenght=14)
                rsi = rsi.to_numpy()[-1]
                sma_20 = ta.sma(_s[close_idx], length=20)
                sma_20 = sma_20.to_numpy()[-1]

            if len(_s) > 50 and good_date:
                sma_50 = ta.sma(_s[close_idx], length=50)
                sma_50 = sma_50.to_numpy()[-1]

            cursor.execute(
                """
                INSERT INTO stock_price (
                    stock_id, date, open, high, low, close, volume,
                sma_20, sma_50, rsi_14)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    stock_id,
                    bar.t.date(),
                    bar.o,
                    bar.h,
                    bar.l,
                    bar.c,
                    bar.v,
                    sma_20,
                    sma_50,
                    rsi,
                ),
            )

connection.commit()
