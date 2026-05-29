import anthropic
import json

client = anthropic.Anthropic()

SYSTEM = """You are an ICT Fair Value Gap (FVG) specialist for the Daily timeframe.

FVG Detection (three-candle pattern):
- Bullish FVG: candle[0].high < candle[2].low  →  gap zone = [candle[0].high, candle[2].low]
- Bearish FVG: candle[0].low > candle[2].high  →  gap zone = [candle[2].high, candle[0].low]

Priority rules:
- Most recent unfilled FVG takes priority
- An FVG is "filled" when price trades through the entire zone
- FVGs align with NWOG/NDOG direction are highest priority

Return structured JSON only."""


def analyze_fvg(daily_candles: list, current_price: float) -> dict:
    prompt = f"""Scan these daily candles for Fair Value Gaps (FVGs).

Daily candles (oldest first, index 0 = oldest): {json.dumps(daily_candles)}
Current price: {current_price}

For each consecutive triplet candle[i], candle[i+1], candle[i+2]:
- Check bullish FVG: candle[i].high < candle[i+2].low
- Check bearish FVG: candle[i].low > candle[i+2].high

List all valid FVGs found. For each, determine if it is filled based on subsequent candles.
Report the most recent unfilled FVG as nearest_fvg.

Respond with only this JSON (no markdown):
{{
  "fvgs": [
    {{
      "type": "bullish" | "bearish",
      "top": float,
      "bottom": float,
      "candle_start_index": int,
      "filled": bool,
      "price_inside": bool,
      "pips_from_price": float
    }}
  ],
  "nearest_fvg": {{same structure or null}},
  "bias": "bullish" | "bearish" | "neutral",
  "summary": "one sentence"
}}"""

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=768,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "{}")
    try:
        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return {"error": "parse_failed", "raw": text[:200]}
