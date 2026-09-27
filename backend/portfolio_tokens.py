"""Portfolio requests have no application-imposed output token ceiling."""

OUTPUT_LIMIT_KEYS = frozenset({"max_tokens", "max_completion_tokens", "max_output_tokens"})


def without_output_limit(settings: dict) -> dict:
    # Also strip legacy callers' limits, including provider-specific spellings.
    return {key: value for key, value in settings.items() if key not in OUTPUT_LIMIT_KEYS}
