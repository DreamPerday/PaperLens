# DeepSeek pricing (CNY per million tokens)
# Model: deepseek-v4-flash
PRICING = {
    "deepseek-v4-flash": {
        "input_cache_hit": 0.02,
        "input_cache_miss": 1.0,
        "output": 2.0,
    },
    # Default fallback
    "default": {
        "input_cache_hit": 0.0,
        "input_cache_miss": 1.0,
        "output": 2.0,
    },
}


def calculate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    cached_tokens: int = 0,
    model: str = "deepseek-v4-flash",
) -> float:
    """Calculate total cost in CNY.

    Args:
        prompt_tokens: Total input (prompt) tokens
        completion_tokens: Output (completion) tokens
        cached_tokens: Cache-hit input tokens (subset of prompt_tokens)
        model: Model name for pricing lookup

    Returns:
        Total cost in CNY
    """
    rates = PRICING.get(model, PRICING["default"])

    cache_miss_tokens = max(0, prompt_tokens - cached_tokens)

    cost = (
        cached_tokens / 1_000_000 * rates["input_cache_hit"]
        + cache_miss_tokens / 1_000_000 * rates["input_cache_miss"]
        + completion_tokens / 1_000_000 * rates["output"]
    )
    return round(cost, 6)