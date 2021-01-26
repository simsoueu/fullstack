import sqlite3
import config
import alpaca_trade_api as tradeapi
from datetime import date
from timezone import is_dst

connection = sqlite3.connect(config.DB_FILE)
connection.row_factory = sqlite3.Row

cursor = connection.cursor()

cursor.execute(
    """
    SELECT id FROM strategy
    WHERE name = 'opening_range_breakout'
"""
)

strategy_id = cursor.fetchone()["id"]

cursor.execute(
    """
    SELECT symbol, company
    FROM stock
    JOIN stock_strategy ON stock_strategy.stock_id = stock.id
    WHERE stock_strategy.strategy_id = ?
""",
    (strategy_id,),
)

stocks = cursor.fetchall()
symbols = list(dict.fromkeys([stock["symbol"] for stock in stocks]))

# print(symbols)

current_date = "2021-1-25"  # date.today().isoformat()

if is_dst():
    start_minute_bar = f"{current_date} 09:30:00-05:00"
    end_minute_bar = f"{current_date} 09:30:00-05:00"
else:
    start_minute_bar = f"{current_date} 09:30:00-04:00"
    end_minute_bar = f"{current_date} 09:30:00-04:00"

api = tradeapi.REST(config.POLY_KEY, config.SECRET_KEY, base_url=config.API_URL)

orders = api.list_orders(status="all", limit=500, after=current_date)
existing_order_symbols = [
    order.symbol for order in orders if order.status != "canceled"
]

messages = []

for symbol in symbols:
    minute_bars = api.polygon.historic_agg_v2(
        symbol, 1, "minute", _from=current_date, to=current_date
    ).df

    opening_range_mask = (minute_bars.index >= start_minute_bar) & (
        minute_bars.index < end_minute_bar
    )
    opening_range_bars = minute_bars.loc[opening_range_mask]
    # print("opening_range_bars:" + opening_range_bars)

    opening_range_low = opening_range_bars["low"].min()
    opening_range_high = opening_range_bars["high"].max()
    opening_range = opening_range_high - opening_range_low

    # print(opening_range_low)
    # print(opening_range_high)
    # print(opening_range)

    after_opening_range_mask = minute_bars.index >= end_minute_bar
    after_opening_range_bars = minute_bars.loc[after_opening_range_mask]

    after_opening_range_breakout = after_opening_range_bars[
        after_opening_range_bars["close"] > opening_range_high
    ]

    if not after_opening_range_breakout.empty:
        if symbol not in existing_order_symbols:
            limit_price = after_opening_range_breakout.ilo

            print(
                f"placing order for {symbol} at {limit_price}, closed_above {opening_range_high}"
            )

            api.submit_order(
                symbol=symbol,
                side="buy",
                type="limit",
                qty=100,
                time_in_force="day",
                order_class="braket",
                limit_price=limit_price,
                take_profit=dict(
                    limit_price=limit_price + opening_range,
                ),
                stop_loss=dict(
                    stop_price=(limit_price - opening_range),
                ),
            )
        else:
            print(f"Already an order for {symbol}, skipping")