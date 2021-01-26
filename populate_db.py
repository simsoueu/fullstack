import sqlite3
import config
import alpaca_trade_api as tradeapi

connection = sqlite3.connect(config.DB_FILE)

connection.row_factory = sqlite3.Row

cursor = connection.cursor()

api = tradeapi.REST(
    config.API_KEY, config.SECRET_KEY, config.API_URL
)  # or use ENV Vars shown below
assets = api.list_assets()

cursor.execute(
    """
    SELECT symbol, company FROM stock
"""
)
rows = cursor.fetchall()
symbols = [row["symbol"] for row in rows]

for asset in assets:
    procced = asset.status == "active" and asset.tradable
    try:
        if procced and asset.symbol not in symbols:
            # print(f"Added a new stock {asset}")
            cursor.execute(
                "INSERT INTO stock  (symbol, company, exchange) VALUES (?, ?, ?)",
                (asset.symbol, asset.name, asset.exchange),
            )
    except Exception as e:
        print(asset.symbol)
        print(e)

connection.commit()
