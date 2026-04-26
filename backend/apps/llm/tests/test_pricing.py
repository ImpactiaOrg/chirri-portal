from decimal import Decimal

from apps.llm.pricing import calculate_cost, get_provider, MODEL_PRICING


def test_get_provider_returns_fireworks_for_kimi():
    assert get_provider("accounts/fireworks/models/kimi-k2-instruct-0905") == "fireworks"


def test_get_provider_unknown_model_returns_default():
    # Default keeps "fireworks" but with zero pricing — we still return a provider
    # so the consumer gets a clear "missing key" error from the client, not a KeyError here.
    assert get_provider("unknown-model-xyz") == "fireworks"


def test_calculate_cost_known_model():
    # Kimi K2: input 0.6 / output 2.5 per 1M.
    cost = calculate_cost(
        "accounts/fireworks/models/kimi-k2-instruct-0905",
        input_tokens=1_000_000, output_tokens=1_000_000,
    )
    assert cost == Decimal("3.100000")


def test_calculate_cost_partial_tokens():
    cost = calculate_cost(
        "accounts/fireworks/models/kimi-k2-instruct-0905",
        input_tokens=500, output_tokens=200,
    )
    # 500/1M * 0.6 + 200/1M * 2.5 = 0.0003 + 0.0005 = 0.0008
    assert cost == Decimal("0.000800")


def test_calculate_cost_unknown_model_is_zero():
    assert calculate_cost("unknown", 1000, 1000) == Decimal("0E-6")


def test_pricing_table_includes_fireworks_kimi_models():
    keys = set(MODEL_PRICING.keys())
    assert "accounts/fireworks/models/kimi-k2-instruct-0905" in keys
    assert "accounts/fireworks/models/kimi-k2p5" in keys
