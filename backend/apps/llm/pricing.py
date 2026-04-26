"""Model pricing table + cost calculator for apps.llm.

USD per 1M tokens. Update manually when a provider changes prices.
Each entry declares its provider so the client knows which SDK/base_url to use.

Sources cached 2026-04-25: fireworks.ai/pricing, openai.com/pricing,
anthropic.com/pricing.
"""
from decimal import Decimal

MODEL_PRICING: dict[str, dict] = {
    # Fireworks
    "accounts/fireworks/models/kimi-k2-instruct-0905": {
        "provider": "fireworks",
        "input_per_1m": Decimal("0.6"),
        "output_per_1m": Decimal("2.5"),
    },
    "accounts/fireworks/models/kimi-k2p5": {
        "provider": "fireworks",
        "input_per_1m": Decimal("0.6"),
        "output_per_1m": Decimal("2.5"),
    },
    # Templates kept commented — uncomment when adding the provider:
    # "gpt-4o": {
    #     "provider": "openai",
    #     "input_per_1m": Decimal("2.5"),
    #     "output_per_1m": Decimal("10.0"),
    # },
    # "claude-sonnet-4-5": {
    #     "provider": "anthropic",
    #     "input_per_1m": Decimal("3.0"),
    #     "output_per_1m": Decimal("15.0"),
    # },
}

# When the model is unknown we still return a provider (fireworks) so the
# pipeline reaches the client and surfaces a clear "missing key" or "unknown
# model" error instead of a KeyError deep in pricing.
DEFAULT_PRICING: dict = {
    "provider": "fireworks",
    "input_per_1m": Decimal("0"),
    "output_per_1m": Decimal("0"),
}


def get_provider(model: str) -> str:
    return MODEL_PRICING.get(model, DEFAULT_PRICING)["provider"]


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    p = MODEL_PRICING.get(model, DEFAULT_PRICING)
    return (
        (Decimal(input_tokens) / Decimal(1_000_000)) * p["input_per_1m"]
        + (Decimal(output_tokens) / Decimal(1_000_000)) * p["output_per_1m"]
    ).quantize(Decimal("0.000001"))
