"""Shared Ollama chat model factory for PM and subagents."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama

from nam_agentic.settings import settings


def build_chat_model() -> BaseChatModel:
    """Build the Ollama chat model with NAM defaults.

    gemma4 and other thinking models put visible text in Ollama's ``thinking``
    field unless ``reasoning=False`` — LangChain then exposes empty ``content``.

    ``num_ctx`` must exceed the PM system prompt (~8k tokens); otherwise Ollama
    only leaves a few dozen tokens for the reply and streaming stops mid-sentence.
    """
    model_name = settings.llm_model.removeprefix("ollama:")
    return ChatOllama(
        model=model_name,
        base_url=settings.llm_base_url,
        num_predict=settings.llm_num_predict,
        num_ctx=settings.llm_num_ctx,
        reasoning=settings.llm_reasoning,
    )
