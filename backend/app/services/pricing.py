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

# Translation input:output ratio estimate for legacy records
_INPUT_RATIO = 0.60


def estimate_segmented_tokens(tokens_used: int) -> tuple[int, int, int]:
    """Estimate (prompt, completion, cached) from total tokens_used.

    For legacy translation records that only have tokens_used without
    segmented fields. Translation typically has input:output ≈ 3:2.
    No cache-hit info available for legacy data.
    """
    if tokens_used <= 0:
        return (0, 0, 0)
    prompt = int(tokens_used * _INPUT_RATIO)
    completion = tokens_used - prompt
    return (prompt, completion, 0)


def normalize_translation_tokens(record: dict) -> tuple[int, int, int, int]:
    """Extract (total, prompt, completion, cached) from a translation record.

    Falls back to estimation from tokens_used for legacy records without
    segmented fields.
    """
    total = record.get("tokens_used", 0)
    prompt = record.get("prompt_tokens", 0)
    completion = record.get("completion_tokens", 0)
    cached = record.get("cached_tokens", 0)
    if prompt == 0 and completion == 0 and total > 0:
        prompt, completion, cached = estimate_segmented_tokens(total)
    return (total, prompt, completion, cached)


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