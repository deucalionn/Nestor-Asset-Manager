from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from nam_agentic.services.chat_messages import (
    find_unsynthesized_task_index,
    text_claims_async_subagent_wait,
    text_claims_missing_market_data_access,
)


def test_text_claims_async_subagent_wait_detects_french_fiction() -> None:
    text = (
        "Je suis en attente de la restitution du sous-agent sector-analyst. "
        "Je ne peux rien faire de plus tant que je n'ai pas reçu les données."
    )
    assert text_claims_async_subagent_wait(text) is True


def test_text_claims_async_subagent_wait_ignores_real_report() -> None:
    text = (
        "STMicroelectronics (STM) est un leader européen des semi-conducteurs. "
        "Le CA 2024 atteint 13,2 Md$, avec une marge brute en reprise. "
        + "Analyse détaillée. " * 40
    )
    assert text_claims_async_subagent_wait(text) is False


def test_text_claims_missing_market_data_access_detects_french_refusal() -> None:
    text = (
        "En tant que PM, je ne peux pas vous fournir de prix en temps réel. "
        "Mes limitations strictes de mes outils m'empêchent d'accéder aux données "
        "de marché en temps réel."
    )
    assert text_claims_missing_market_data_access(text) is True


def test_text_claims_missing_market_data_access_ignores_price_answer() -> None:
    text = "Stellantis (STLA) cotait à 12,45 USD à la dernière clôture selon Yahoo Finance."
    assert text_claims_missing_market_data_access(text) is False


def test_find_unsynthesized_task_index_after_stub() -> None:
    messages = [
        HumanMessage(content="Analyse STM"),
        AIMessage(content="", tool_calls=[{"name": "task", "args": {}, "id": "1"}]),
        ToolMessage(content="Rapport sectoriel complet." * 50, tool_call_id="1", name="task"),
        AIMessage(content="Please give me a moment while I compile the report."),
    ]
    assert find_unsynthesized_task_index(messages) == 2


def test_find_unsynthesized_task_index_cleared_after_long_synthesis() -> None:
    messages = [
        HumanMessage(content="Analyse STM"),
        AIMessage(content="", tool_calls=[{"name": "task", "args": {}, "id": "1"}]),
        ToolMessage(content="Rapport sectoriel complet." * 50, tool_call_id="1", name="task"),
        AIMessage(content="Synthèse détaillée. " * 80),
    ]
    assert find_unsynthesized_task_index(messages) is None
