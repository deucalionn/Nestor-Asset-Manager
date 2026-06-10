def build_chat_message(user_content: str) -> str:
    """Wrap a user chat turn with instructions that override the market-cycle workflow."""
    return (
        "CHAT MODE — suivre prompts/CHAT.md (prime sur write_todos et cycles marché).\n\n"
        "Exécution immédiate, sans annoncer de plan :\n"
        "1. get_user_context + get_portfolio_positions\n"
        "2. task(subagent_type, description) — brief français court (≤200 mots)\n"
        "3. Synthèse finale française obligatoire (répondre à la question, ex. les 300 €)\n\n"
        f"Message utilisateur : {user_content}"
    )


def build_synthesis_nudge(user_question: str) -> str:
    """Follow-up user turn when experts ran but no user-facing answer yet."""
    return (
        "[CHAT — synthèse obligatoire] Les experts ont rendu leurs rapports.\n"
        f"Question client : {user_question}\n\n"
        "Rédigez MAINTENANT la réponse finale en français : synthèse portefeuille + "
        "marché + réponse concrète (ex. que faire des 300 €). "
        "Aucun write_todos, aucun plan, aucun nouvel appel task."
    )
