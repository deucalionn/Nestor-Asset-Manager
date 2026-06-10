from nam_agentic.services.chat_prompt import build_delegation_nudge, build_synthesis_nudge


def test_build_synthesis_nudge_uses_user_question() -> None:
    question = "Que disent les marchés ce soir ?"
    nudge = build_synthesis_nudge(question)
    assert question in nudge
    assert "write_todos" not in nudge.lower() or "no write_todos" in nudge.lower()


def test_build_delegation_nudge_lists_subagents() -> None:
    question = "Quel est le CA de STMicro ?"
    nudge = build_delegation_nudge(question)
    assert question in nudge
    assert "sector-analyst" in nudge
    assert "task()" in nudge


def test_build_delegation_nudge_price_question() -> None:
    nudge = build_delegation_nudge("tu peux récupérer le prix de stellantis ?")
    assert "search_yahoo_symbol" in nudge
    assert "get_asset_price_from_yf" in nudge
