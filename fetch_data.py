import yfinance as yf
from datetime import datetime, timezone


def fetch_market_data(symbol: str = "EURUSD=X", account_balance: float = 10000) -> dict:
    """Fetch real OHLCV data from Yahoo Finance."""
    ticker = yf.Ticker(symbol)

    weekly = ticker.history(period="3mo", interval="1wk")
    daily = ticker.history(period="1mo", interval="1d")

    def to_candles(df):
        candles = []
        for ts, row in df.iterrows():
            candles.append({
                "time": ts.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 5),
                "high": round(float(row["High"]), 5),
                "low": round(float(row["Low"]), 5),
                "close": round(float(row["Close"]), 5),
            })
        return candles

    weekly_candles = to_candles(weekly)[-2:]
    daily_candles = to_candles(daily)[-8:]
    current_price = round(float(ticker.history(period="1d", interval="1m")["Close"].iloc[-1]), 5)

    return {
        "symbol": symbol.replace("=X", ""),
        "account_balance": account_balance,
        "current_price": current_price,
        "weekly_candles": weekly_candles,
        "daily_candles": daily_candles,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


if __name__ == "__main__":
    import json
    data = fetch_market_data()
    print(json.dumps(data, indent=2))
