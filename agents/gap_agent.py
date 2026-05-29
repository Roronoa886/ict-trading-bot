import anthropic
import json

client = anthropic.Anthropic()

SYSTEM = """You are an ICT Gap Analysis specialist. You identify and measure opening gaps.

New Week Opening Gap (NWOG):
- Gap between Friday's close and Sunday's open
- Bullish NWOG: Sunday opens ABOVE Friday close → bias long, look for buys at the gap
- Bearish NWOG: Sunday opens BELOW Friday close → bias short, look for sells at the gap
- Key levels: top, mid-line (50%), bottom

New Day Opening Gap (NDOG):
- Gap between previous day's close and current day's open (midnight NY time)
- Price frequently returns to fill the NDOG mid-line during the session
- Key levels: top, mid-line (50%), bottom

Only report a gap if there is a genuine price difference between the close and next open.
Return structured JSON only."""


def analyze_gaps(weekly_candles: list, daily_candles: list, current_price: float) -> dict:
    prompt = f"""Analyze for NWOG and NDOG gaps.

Weekly candles (oldest first): {json.dumps(weekly_candles)}
Daily candles (oldest first): {json.dumps(daily_candles)}
Current price: {current_price}

Identify:
1. NWOG: compare weekly_candles[-2].close vs weekly_candles[-1].open
2. NDOG: compare daily_candles[-2].close vs daily_candles[-1].open
3. For each gap: calculate top, mid_line, bottom and note direction
4. Is current price within 0.15% of any mid-line?

Respond with only this JSON (no markdown, no explanation):
{{
  "nwog": {{
    "exists": bool,
    "direction": "bullish" | "bearish" | null,
    "top": float | null,
    "mid_line": float | null,
    "bottom": float | null,
    "price_at_midline": bool,
    "gap_size_pips": float | null
  }},
  "ndog": {{
    "exists": bool,
    "direction": "bullish" | "bearish" | null,
    "top": float | null,
    "mid_line": float | null,
    "bottom": float | null,
    "price_at_midline": bool,
    "gap_size_pips": float | null
  }},
  "alignment": "bullish" | "bearish" | "mixed" | "none",
  "summary": "one sentence"
}}"""

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
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
