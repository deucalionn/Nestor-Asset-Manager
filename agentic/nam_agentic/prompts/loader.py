from pathlib import Path


class PromptLoader:
    """Loads agent system prompts from markdown files in the prompts directory."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._dir = prompts_dir or Path(__file__).resolve().parent

    def load(self, name: str) -> str:
        """Load prompt text from ``{name}.md`` (name without extension)."""
        path = self._dir / f"{name}.md"
        return path.read_text(encoding="utf-8").strip()
