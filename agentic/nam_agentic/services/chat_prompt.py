"""Runner helpers for chat finalization nudges."""


def build_synthesis_nudge(user_question: str, *, from_prior_turn: bool = False) -> str:
    """Follow-up when task() ran but no user-facing synthesis was produced."""
    intro = (
        "A subagent task() already completed earlier in this conversation — "
        "find its ToolMessage in the thread history."
        if from_prior_turn
        else "The sector/macro/ETF subagent has finished. "
        "Its report is in your task() ToolMessage from this turn."
    )
    return (
        f"[Final synthesis required] {intro}\n"
        f"User question: {user_question}\n\n"
        "Write the COMPLETE final answer now in the same language as the user question. "
        "Include figures, thesis, and risks from the subagent report. "
        "task() is SYNCHRONOUS — it already finished. "
        "Do NOT say you are waiting for a subagent. Do NOT describe upcoming steps. "
        "No write_todos, no plan preamble, no new task() calls."
    )


def build_delegation_nudge(user_question: str) -> str:
    """Follow-up when the PM answered without delegating to a subagent."""
    price_hint = ""
    lower = user_question.lower()
    if any(word in lower for word in ("prix", "cours", "price", "quote", "cotation")):
        price_hint = (
            "\nThe user asked for a stock price. task(sector-analyst) MUST call "
            "search_yahoo_symbol then get_asset_price_from_yf (Yahoo delayed quote). "
            "Do NOT claim missing market data API.\n"
        )
    return (
        "[Delegation required] You are the PM orchestrator — you cannot fetch company "
        "financials, prices, or deep market research yourself.\n"
        f"User question: {user_question}\n"
        f"{price_hint}\n"
        "Call task() now with the appropriate subagent:\n"
        "- sector-analyst: company price, CA/marges/bilan, equity, sector analysis\n"
        "- macro-strategist: macro, rates, broad market news\n"
        "- etf-quant: ETF composition and passive exposure\n"
        "Include all context in the task description. Then synthesize the result for the user."
    )
