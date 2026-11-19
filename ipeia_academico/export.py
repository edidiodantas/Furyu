"""Exporta a resposta para Markdown, para reaproveitar na escrita de textos."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def extract_answer_text(session: Any) -> str:
    """Texto da resposta, tolerando variações de versão do PQASession."""
    for attr in ("formatted_answer", "answer"):
        value = getattr(session, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(session)


def extract_references(session: Any) -> str:
    value = getattr(session, "references", None)
    return value.strip() if isinstance(value, str) else ""


def answer_to_markdown(
    question: str, answer: str, references: str, *, model: str, generated_at: datetime
) -> str:
    """Monta um .md com pergunta, resposta e referências."""
    parts = [
        "# Resposta do IPeia Acadêmico",
        "",
        f"- **Data:** {generated_at.strftime('%Y-%m-%d %H:%M')}",
        f"- **Modelo:** {model}",
        "",
        "## Pergunta",
        "",
        question.strip(),
        "",
        "## Resposta",
        "",
        answer.strip(),
        "",
    ]
    if references and references not in answer:
        parts += ["## Referências", "", references, ""]
    parts += [
        "---",
        "_Gerado por IA local a partir do seu acervo. Confira cada citação no "
        "documento original antes de usar em um trabalho acadêmico._",
        "",
    ]
    return "\n".join(parts)
