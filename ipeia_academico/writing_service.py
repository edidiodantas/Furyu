"""Modos de escrita: resumo de um documento e texto acadêmico por seções.

Não conhece Streamlit. Usa o `ResearchService` para o acervo e a formatação
ABNT, e recebe por injeção a função que dá as Settings de cada modo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ipeia_academico.academic_prompts import (
    Mode,
    WritingInputError,
    parse_sections,
    section_request,
    summary_request,
    validate_theme,
)
from ipeia_academico.citations import FormattedAnswer, merge_references
from ipeia_academico.research_service import AnswerResult, ResearchService

SettingsForMode = Callable[[Mode], Any]


@dataclass(frozen=True)
class WrittenSection:
    title: str
    result: AnswerResult


@dataclass(frozen=True)
class AcademicText:
    theme: str
    sections: tuple[WrittenSection, ...]
    combined: FormattedAnswer  # texto de todas as seções + referências únicas


class AcademicWriter:
    def __init__(self, service: ResearchService, settings_for_mode: SettingsForMode) -> None:
        self._service = service
        self._settings_for_mode = settings_for_mode

    async def summarize_document(self, docname: str, language: str) -> AnswerResult:
        """Resumo de UM documento: a busca de trechos fica restrita a ele.

        Monta uma coleção temporária só com os trechos desse documento. Os
        trechos já têm embedding, então nada é recalculado.
        """
        request = summary_request(docname, language)
        docs = self._service.docs
        doc = next((d for d in docs.docs.values() if d.docname == docname), None)
        if doc is None:
            raise WritingInputError(f"Documento {docname!r} não está no índice.")
        texts = [t for t in docs.texts if t.doc.dockey == doc.dockey]
        if not texts:
            raise WritingInputError(f"O documento {docname!r} não tem trechos indexados.")

        settings = self._settings_for_mode(Mode.SUMMARY)
        scoped = self._service.new_docs()
        await scoped.aadd_texts(texts, doc, settings=settings)
        session = await scoped.aquery(request, settings=settings)
        return AnswerResult(session, self._service.format_session(session))

    def plan_text(self, theme: str, sections_raw: str) -> tuple[str, list[str]]:
        """Valida o pedido antes de gastar chamadas à IA."""
        theme = validate_theme(theme)
        sections = parse_sections(sections_raw)
        if not self._service.has_documents():
            raise WritingInputError("O acervo está vazio. Envie ou baixe documentos primeiro.")
        return theme, sections

    async def write_section(
        self, theme: str, title: str, sections: list[str], language: str
    ) -> WrittenSection:
        """Uma seção, com sua própria busca no acervo.

        Uma busca por seção traz trechos específicos para cada parte do texto;
        uma única pergunta grande traria só os trechos mais genéricos.
        """
        settings = self._settings_for_mode(Mode.ACADEMIC_TEXT)
        session = await self._service.docs.aquery(
            section_request(theme, title, sections, language), settings=settings
        )
        return WrittenSection(title, AnswerResult(session, self._service.format_session(session)))

    @staticmethod
    def assemble(theme: str, written: list[WrittenSection]) -> AcademicText:
        combined = merge_references(
            FormattedAnswer(
                f"## {w.title}\n\n{w.result.formatted.text}",
                w.result.formatted.references,
                w.result.formatted.missing_docnames,
            )
            for w in written
        )
        return AcademicText(theme, tuple(written), combined)

    async def write_text(self, theme: str, sections_raw: str, language: str) -> AcademicText:
        """Texto completo de uma vez (a interface chama seção por seção)."""
        theme, sections = self.plan_text(theme, sections_raw)
        written = [await self.write_section(theme, t, sections, language) for t in sections]
        return self.assemble(theme, written)
