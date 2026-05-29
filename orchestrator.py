import anthropic
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from agents.gap_agent import analyze_gaps
from agents.fvg_agent import analyze_fvg
from agents.risk_agent import calculate_risk

client = anthropic.Anthropic()

SYSTEM = """You are an ICT (Inner Circle Trader) orchestrator that coordinates three specialist agents
to identify high-probability trade setups using Opening Gap methodology.

Strategy — only recommend a trade when ALL THREE are aligned:
1. NWOG and NDOG gaps point in the same direction
2. Daily FVG aligns with gap direction
3. Current time is within a kill zone (London 2am-5am AEST or New York 7pm-10pm AEST)

Entry: at the 50% mid-line of the gap structure
Confirmation needed: displacement candle + FVG on 1min/5min at the entry zone
Minimum RR: 2:1 | Stop: beyond gap high/low

Workflow:
1. Call analyze_market_gaps to assess NWOG and NDOG
2. Call analyze_daily_fvg to identify Daily FVGs
3. If gaps and FVG align AND kill zone is active → call calculate_risk_parameters
4. Provide a clear TRADE or NO TRADE recommendation with reasoning"""

TOOLS = [
    {
        "name": "analyze_market_gaps",
        "description": "Analyzes NWOG and NDOG from weekly and daily candles. Returns gap levels, direction, mid-lines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "weekly_candles": {
                    "type": "array",
                    "description": "Last 2 weekly OHLCV candles [{time, open, high, low, close}]",
                    "items": {"type": "object"},
                },
                "daily_candles": {
                    "type": "array",
                    "description": "Last 2 daily OHLCV candles [{time, open, high, low, close}]",
                    "items": {"type": "object"},
                },
                "current_price": {"type": "number"},
            },
            "required": ["weekly_candles", "daily_candles", "current_price"],
        },
    },
    {
        "name": "analyze_daily_fvg",
        "description": "Identifies Fair Value Gaps on the Daily timeframe. Returns FVG zones, direction, nearest unfilled FVG.",
        "input_schema": {
            "type": "object",
            "properties": {
                "daily_candles": {
                    "type": "array",
                    "description": "Last 5-10 daily OHLCV candles [{time, open, high, low, close}]",
                    "items": {"type": "object"},
                },
                "current_price": {"type": "number"},
            },
            "required": ["daily_candles", "current_price"],
        },
    },
    {
        "name": "calculate_risk_parameters",
        "description": "Calculates stop loss, take profit, lot size, and dollar risk for a valid setup.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["long", "short"]},
                "entry_price": {"type": "number", "description": "Entry at gap mid-line"},
                "gap_top": {"type": "number"},
                "gap_bottom": {"type": "number"},
                "account_balance": {"type": "number"},
                "risk_percent": {"type": "number", "default": 1.0},
            },
            "required": ["direction", "entry_price", "gap_top", "gap_bottom", "account_balance"],
        },
    },
]


def _kill_zone_status() -> dict:
    aest = ZoneInfo("Australia/Sydney")
    now = datetime.now(aest)
    h = now.hour
    if 2 <= h < 5:
        return {"active": True, "session": "London", "time": now.strftime("%H:%M AEST")}
    if 19 <= h < 22:
        return {"active": True, "session": "New York", "time": now.strftime("%H:%M AEST")}
    return {"active": False, "session": None, "time": now.strftime("%H:%M AEST")}


def _dispatch_tool(name: str, inputs: dict) -> str:
    if name == "analyze_market_gaps":
        result = analyze_gaps(
            inputs["weekly_candles"],
            inputs["daily_candles"],
            inputs["current_price"],
        )
    elif name == "analyze_daily_fvg":
        result = analyze_fvg(inputs["daily_candles"], inputs["current_price"])
    elif name == "calculate_risk_parameters":
        result = calculate_risk(
            inputs["direction"],
            inputs["entry_price"],
            inputs["gap_top"],
            inputs["gap_bottom"],
            inputs["account_balance"],
            inputs.get("risk_percent", 1.0),
        )
    else:
        result = {"error": f"unknown tool: {name}"}
    return json.dumps(result)


def run(market_data: dict) -> dict:
    """Run the full ICT multi-agent analysis pipeline."""
    kill_zone = _kill_zone_status()

    user_message = f"""Analyze this market data for an ICT trade setup.

Kill zone status: {json.dumps(kill_zone)}
Symbol: {market_data.get('symbol', 'EURUSD')}
Account balance: ${market_data.get('account_balance', 10000):,}
Current price: {market_data['current_price']}

Available data:
- weekly_candles: {len(market_data.get('weekly_candles', []))} candles
- daily_candles: {len(market_data.get('daily_candles', []))} candles

Full market data: {json.dumps(market_data, indent=2)}

Use your tools to analyse gaps and FVGs, then give a clear TRADE or NO TRADE recommendation."""

    messages = [{"role": "user", "content": user_message}]

    while True:
        with client.messages.stream(
            model="claude-opus-4-7",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            recommendation = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return {
                "recommendation": recommendation,
                "kill_zone": kill_zone,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "cache_read_tokens": response.usage.cache_read_input_tokens,
                },
            }

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result_str = _dispatch_tool(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})
