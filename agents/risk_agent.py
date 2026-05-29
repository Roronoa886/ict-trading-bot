import anthropic
import json

client = anthropic.Anthropic()

SYSTEM = """You are an ICT Risk Management specialist.

Rules:
- Stop loss: placed BEYOND the gap extreme (longs: below gap bottom with 0.05% buffer; shorts: above gap top with 0.05% buffer)
- Minimum 2:1 risk-to-reward; 3:1 is the extended target
- Dollar risk = account_balance × (risk_percent / 100)
- Position size (Forex, 5-decimal pairs): lot_size = dollar_risk / (stop_distance_in_price × 100000)
- Take profit 1 = entry ± (stop_distance × 2)
- Take profit 2 = entry ± (stop_distance × 3)

Reject the setup if stop distance is less than 5 pips or RR is below 2:1.
Return structured JSON only."""


def calculate_risk(
    direction: str,
    entry_price: float,
    gap_top: float,
    gap_bottom: float,
    account_balance: float,
    risk_percent: float = 1.0,
) -> dict:
    prompt = f"""Calculate risk parameters for this ICT trade.

Direction: {direction}
Entry (gap mid-line): {entry_price}
Gap top: {gap_top}
Gap bottom: {gap_bottom}
Account balance: {account_balance}
Risk per trade: {risk_percent}%

Calculate stop loss, take profit levels, lot size, and dollar risk.
Validate the setup meets minimum 2:1 RR and 5 pip stop distance.

Respond with only this JSON (no markdown):
{{
  "valid": bool,
  "rejection_reason": "string or null",
  "entry": float,
  "stop_loss": float,
  "stop_distance_pips": float,
  "dollar_risk": float,
  "take_profit_1": float,
  "take_profit_2": float,
  "rr_tp1": float,
  "rr_tp2": float,
  "lot_size": float,
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
