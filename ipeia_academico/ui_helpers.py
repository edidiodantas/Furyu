"""Funções puras usadas pela interface (sem importar Streamlit)."""

from __future__ import annotations

import re
from typing import Any

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~])")


def escape_markdown(text: str) -> str:
    """Escapa texto vindo de APIs externas antes de ir para st.markdown.

    Títulos de catálogos podem conter `[x](javascript:...)` ou `*` que
    quebrariam a formatação ou gerariam links inesperados.
    """
    return _MD_SPECIAL.sub(r"\\\1", text or "")


def hit_button_key(index: int, hit: Any) -> str:
    """Key única para o botão de cada resultado de busca.

    O índice garante unicidade mesmo com títulos repetidos e IDs vazios.
    """
    raw = getattr(hit, "paper_id", "") or getattr(hit, "doi", "") or getattr(hit, "title", "")
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", raw)[:50]
    return f"idx-{index}_{slug}"


def format_score(score: Any) -> str:
    if isinstance(score, (int, float)):
        return f"{score:g}"
    return ""
