class LLMError(Exception):
    """Base for all apps.llm exceptions."""


class LLMConfigError(LLMError):
    """Provider misconfigured (missing API key, unknown SDK, etc.)."""


class LLMValidationError(LLMError):
    """Output failed JSON parsing or schema validation after retries."""


class LLMCostExceededError(LLMError):
    """Call would exceed LLM_MAX_TOKENS_PER_CALL or LLM_MAX_COST_PER_JOB_USD."""
