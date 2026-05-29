import json
from orchestrator import run

# Sample market data — replace with real data from your broker/feed
market_data = {
    "symbol": "EURUSD",
    "account_balance": 10000,
    "current_price": 1.08750,

    # Last 2 weekly candles (prev week + current week)
    "weekly_candles": [
        {"time": "2024-01-08", "open": 1.09200, "high": 1.09850, "low": 1.08600, "close": 1.08950},
        {"time": "2024-01-15", "open": 1.09100, "high": 1.09200, "low": 1.08700, "close": 1.08750},
    ],

    # Last 5 daily candles (FVG analysis needs 3+ candles)
    "daily_candles": [
        {"time": "2024-01-09", "open": 1.09300, "high": 1.09500, "low": 1.09100, "close": 1.09200},
        {"time": "2024-01-10", "open": 1.09150, "high": 1.09400, "low": 1.08900, "close": 1.09350},
        {"time": "2024-01-11", "open": 1.09300, "high": 1.09450, "low": 1.08750, "close": 1.08900},
        {"time": "2024-01-12", "open": 1.08950, "high": 1.09100, "low": 1.08600, "close": 1.08750},
        {"time": "2024-01-14", "open": 1.08820, "high": 1.09200, "low": 1.08700, "close": 1.08820},
        # Today
        {"time": "2024-01-15", "open": 1.08900, "high": 1.09100, "low": 1.08700, "close": 1.08750},
    ],
}

if __name__ == "__main__":
    print("=" * 60)
    print("ICT Multi-Agent Trading Bot")
    print("=" * 60)
    print(f"Symbol:  {market_data['symbol']}")
    print(f"Price:   {market_data['current_price']}")
    print(f"Balance: ${market_data['account_balance']:,}")
    print("=" * 60)
    print("Running analysis...\n")

    result = run(market_data)

    print("\n" + "=" * 60)
    print("ANALYSIS RESULT")
    print("=" * 60)
    kz = result["kill_zone"]
    status = f"ACTIVE — {kz['session']}" if kz["active"] else "INACTIVE"
    print(f"Kill Zone: {status} ({kz['time']})")
    print()
    print(result["recommendation"])
    print()
    usage = result["usage"]
    print(f"Tokens — input: {usage['input_tokens']} | output: {usage['output_tokens']} | cache hits: {usage['cache_read_tokens']}")
