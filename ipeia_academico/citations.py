"""Troca as chaves de citação do PaperQA2 por citações ABNT (função pura).

Como o PaperQA2 cita: o modelo escreve chaves como `(pqac-0f650d59)`, uma por
trecho de evidência (Context.id). O próprio PaperQA2 as troca por
"Docname pages 3-4". Aqui fazemos a troca a partir da `raw_answer` usando os
dados bibliográficos que você informou, gerando (Silva, 2020, p. 3-4) e a
lista de referências em ordem alfabética.

Documento sem dados ABNT: a citação usa o nome interno do documento e a
referência é a que o PaperQA2 montou, marcada para você completar.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ipeia_academico.abnt import (
    BibReference,
    format_citation_inner,
    format_reference,
    page_locator,
    reference_sort_key,
)

_KEY_RE = re.compile(r"\bpqac-[a-zA-Z0-9]{8}\b")
_PAREN_WITH_KEY_RE = re.compile(r"\(([^()]*\bpqac-[a-zA-Z0-9]{8}\b[^()]*)\)")
_PAGES_RE = re.compile(r"\bpages?\s+(\d+(?:\s*-\s*\d+)?)\s*$")
MISSING_DATA_NOTE = "[dados ABNT não preenchidos]"


@dataclass(frozen=True)
class SourceRef:
    """Um trecho citável: de qual documento e de quais páginas."""

    docname: str
    pages: str
    fallback_citation: str


@dataclass(frozen=True)
class FormattedAnswer:
    text: str
    references: tuple[str, ...]
    missing_docnames: tuple[str, ...]


def pages_from_text_name(text_name: str) -> str:
    """"Silva2020 pages 3-4" → "3-4". Arquivos .txt/.md não têm página."""
    match = _PAGES_RE.search(text_name or "")
    if not match:
        return ""
    pages = re.sub(r"\s+", "", match.group(1))
    first, _, last = pages.partition("-")
    return first if last == first else pages  # "12-12" → "12"


def sources_from_contexts(contexts: Iterable[Any]) -> dict[str, SourceRef]:
    """Mapa Context.id → SourceRef, tolerando objetos incompletos."""
    sources: dict[str, SourceRef] = {}
    for ctx in contexts or []:
        key = getattr(ctx, "id", "")
        text = getattr(ctx, "text", None)
        doc = getattr(text, "doc", None)
        docname = getattr(doc, "docname", "") or ""
        if not key or not docname:
            continue
        sources[key] = SourceRef(
            docname=docname,
            pages=pages_from_text_name(getattr(text, "name", "")),
            fallback_citation=getattr(doc, "formatted_citation", "") or docname,
        )
    return sources


def _inner_citation(source: SourceRef, ref: BibReference | None, uppercase: bool) -> str:
    if ref is not None:
        return format_citation_inner(ref, source.pages, uppercase=uppercase)
    locator = page_locator(source.pages)
    return f"{source.docname}, {locator}" if locator else source.docname


def format_answer(
    raw_answer: str,
    sources: Mapping[str, SourceRef],
    references: Mapping[str, BibReference],
    *,
    uppercase: bool = False,
) -> FormattedAnswer:
    """Texto com citações ABNT + lista de referências dos documentos citados.

    `references` é indexado pelo docname do PaperQA2. Chaves inventadas pelo
    modelo (que não existem nos trechos) são removidas.
    """
    cited: dict[str, None] = {}

    def citation_for(keys: list[str]) -> str:
        inner_parts: dict[str, None] = {}
        for key in keys:
            source = sources.get(key)
            if source is None:
                continue
            cited[source.docname] = None
            inner_parts[_inner_citation(source, references.get(source.docname), uppercase)] = None
        return f"({'; '.join(inner_parts)})" if inner_parts else ""

    text = _PAREN_WITH_KEY_RE.sub(lambda m: citation_for(_KEY_RE.findall(m.group(1))), raw_answer or "")
    # Chaves soltas, fora de parênteses (acontece com modelos pequenos).
    text = _KEY_RE.sub(lambda m: citation_for([m.group(0)]), text)
    text = re.sub(r"[ \t]+([.,;:])", r"\1", re.sub(r"[ \t]{2,}", " ", text)).strip()

    reference_list: list[str] = []
    missing: list[str] = []
    fallback_by_doc = {s.docname: s.fallback_citation for s in sources.values()}
    for docname in cited:
        ref = references.get(docname)
        if ref is None:
            missing.append(docname)
            reference_list.append(f"{fallback_by_doc[docname]} {MISSING_DATA_NOTE}")
        else:
            reference_list.append(format_reference(ref))
    return FormattedAnswer(
        text=text,
        references=tuple(sorted(dict.fromkeys(reference_list), key=reference_sort_key)),
        missing_docnames=tuple(missing),
    )


def merge_references(answers: Iterable[FormattedAnswer]) -> FormattedAnswer:
    """Junta as referências de várias seções numa lista única, sem repetição."""
    answers = list(answers)
    refs = {r: None for a in answers for r in a.references}
    missing = {m: None for a in answers for m in a.missing_docnames}
    return FormattedAnswer(
        text="\n\n".join(a.text for a in answers),
        references=tuple(sorted(refs, key=reference_sort_key)),
        missing_docnames=tuple(missing),
    )
