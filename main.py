import sqlite3
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse


import config

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/")
def index(request: Request):
    stock_filter = request.query_params.get("filter", False)

    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    if stock_filter == "new_closing_highs":
        cursor.execute(
            """
            SELECT *
            FROM (
                SELECT symbol, company, stock_id, max(close), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            )
            WHERE date = (select max(date) from stock_price);
        """
        )
    elif stock_filter == "new_closing_lows":
        cursor.execute(
            """
            SELECT *
            FROM (
                SELECT symbol, company, stock_id, min(close), date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                GROUP BY stock_id
                ORDER BY symbol
            )
            WHERE date = (select max(date) from stock_price);
        """
        )
    elif stock_filter == "rsi_overbought":
        cursor.execute(
            """
                SELECT symbol, company, stock_id, date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                WHERE rsi_14 > 70
                and date = (select max(date) from stock_price)
                ORDER BY symbol
        """
        )
    elif stock_filter == "rsi_oversold":
        cursor.execute(
            """
            SELECT symbol, company, stock_id, date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                WHERE rsi_14 < 30
                and date = (select max(date) from stock_price)
                ORDER BY symbol
        """
        )
    elif stock_filter == "above_sma_20":
        cursor.execute(
            """
            SELECT symbol, company, stock_id, date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                WHERE close > sma_20
                and date = (select max(date) from stock_price)
                ORDER BY symbol
        """
        )
    elif stock_filter == "below_sma_20":
        cursor.execute(
            """
            SELECT symbol, company, stock_id, date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                WHERE close < sma_20
                and date = (select max(date) from stock_price)
                ORDER BY symbol
        """
        )
    elif stock_filter == "above_sma_50":
        cursor.execute(
            """
            SELECT symbol, company, stock_id, date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                WHERE close > sma_50
                and date = (select max(date) from stock_price)
                ORDER BY symbol
        """
        )
    elif stock_filter == "below_sma_50":
        cursor.execute(
            """
            SELECT symbol, company, stock_id, date
                FROM stock_price JOIN stock ON stock.id = stock_price.stock_id
                WHERE close < sma_50
                and date = (select max(date) from stock_price)
                ORDER BY symbol
        """
        )
    else:
        cursor.execute(
            """
            SELECT id, symbol, company FROM stock ORDER BY symbol
        """
        )

    rows = cursor.fetchall()

    cursor.execute(
        """
        SELECT symbol, rsi_14, sma_20, sma_50, close
        from stock join stock_price on stock_price.stock_id = stock.id
        where date = (select max(date) from stock_price) and rsi_14 is not null
    """
    )

    indicator_rows = cursor.fetchall()
    indicator_values = {}

    for row in indicator_rows:
        indicator_values[row["symbol"]] = row

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "stocks": rows, "indicator_values": indicator_values},
    )


@app.get("/stock/{symbol}")
def stock_detail(request: Request, symbol):
    print(symbol)
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT * FROM strategy
    """
    )

    strategies = cursor.fetchall()

    cursor.execute(
        """
        SELECT id, symbol, company, exchange FROM stock WHERE symbol = ?
    """,
        (symbol,),
    )

    row = cursor.fetchone()

    cursor.execute(
        """
        SELECT * FROM stock_price WHERE stock_id = ?
    """,
        (row["id"],),
    )

    prices = cursor.fetchall()

    return templates.TemplateResponse(
        "stock_detail.html",
        {"request": request, "stock": row, "bars": prices, "strategies": strategies},
    )


@app.post("/appy_strategy")
def appy_strategy(strategy_id: int = Form(...), stock_id: int = Form(...)):
    connection = sqlite3.connect(config.DB_FILE)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO stock_strategy (stock_id, strategy_id) VALUES (?, ?)
    """,
        (stock_id, strategy_id),
    )

    connection.commit()

    return RedirectResponse(url=f"/strategy/{strategy_id}", status_code=303)


@app.get("/strategies")
def strategies(request: Request):
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT * FROM strategy
    """
    )

    strategies = cursor.fetchall()

    return templates.TemplateResponse(
        "strategies.html", {"request": request, "strategies": strategies}
    )


@app.get("/orders")
def orders(request: Request):
    return templates.TemplateResponse("orders.html", {"request": request})


@app.get("/strategy/{strategy_id}")
def strategy(request: Request, strategy_id):
    connection = sqlite3.connect(config.DB_FILE)
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, name FROM strategy
        WHERE id = ?
    """,
        (strategy_id,),
    )

    strategy = cursor.fetchone()

    cursor.execute(
        """
        SELECT symbol, company
        FROM stock JOIN stock_strategy ON stock_strategy.stock_id = stock.id
        WHERE strategy_id = ?
    """,
        (strategy_id,),
    )

    stocks = cursor.fetchall()

    return templates.TemplateResponse(
        "strategy.html", {"request": request, "stocks": stocks, "strategy": strategy}
    )
