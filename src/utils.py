import traceback

def clamp(n, minn, maxn):
    """Clamps a value between a minimum and maximum."""
    return max(minn, min(n, maxn))

def log_exception(context: str, e: Exception):
    """Standardized exception logging with traceback."""
    print(f"❌ [{context}] Error: {e}")
    traceback.print_exc()

def apply_cognitive_load_overrides(strategy: dict | str, cog_load: float) -> dict | str:
    """
    Overrides the active strategy if cognitive load is too high.
    Returns the modified strategy (usually fragmented thoughts).
    """
    if cog_load > 0.7:
        return {"fragmented_thoughts": 1.0}
    return strategy
