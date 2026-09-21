import os

_llm = None
_current_config = None


def get_llm():
    """Returns a LangChain chat model. Provider picked via LLM_PROVIDER env
    var: "gemini" (default, uses your Google Gemini API key) or "claude"
    (uses your Anthropic API key). Both are LangChain chat models, so
    nothing else in Agent/agents/composer.py needs to change either way.
    """
    global _llm, _current_config
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    current_model = (
        os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if provider == "gemini"
        else os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    )
    cache_key = (provider, current_model)

    if _llm is not None and _current_config == cache_key:
        return _llm

    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        primary_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        primary_llm = ChatGoogleGenerativeAI(
            model=primary_model,
            google_api_key=api_key,
            temperature=0.4,
        )

        # Fallback model in case primary model hits rate limit or quota exhaustion
        fallback_models = ["gemini-2.5-flash-lite", "gemini-2.5-flash"]
        fallbacks = [
            ChatGoogleGenerativeAI(
                model=m,
                google_api_key=api_key,
                temperature=0.4,
            )
            for m in fallback_models
            if m != primary_model
        ]
        _llm = primary_llm.with_fallbacks(fallbacks) if fallbacks else primary_llm
    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic

        _llm = ChatAnthropic(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.4,
        )
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Use 'gemini' or 'claude'."
        )

    _current_config = cache_key
    return _llm
