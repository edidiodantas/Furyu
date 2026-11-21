"""Seção "Pergunta / Resumo / Texto acadêmico" e exibição do resultado."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import streamlit as st

from ipeia_academico.academic_prompts import DEFAULT_SECTIONS, Mode, WritingInputError
from ipeia_academico.citations import FormattedAnswer
from ipeia_academico.config import AppConfig
from ipeia_academico.export import document_to_markdown
from ipeia_academico.research_service import QuestionError, ResearchService
from ipeia_academico.ui_helpers import format_score
from ipeia_academico.writing_service import AcademicWriter

RunAsync = Callable[[Coroutine[Any, Any, Any]], Any]

_MODE_LABELS = {
    Mode.QUESTION: "Pergunta",
    Mode.SUMMARY: "Resumo de documento",
    Mode.ACADEMIC_TEXT: "Texto acadêmico",
}
_TITLES = {
    Mode.QUESTION: "Resposta do IPeia Acadêmico",
    Mode.SUMMARY: "Resumo",
    Mode.ACADEMIC_TEXT: "Texto acadêmico",
}


@dataclass(frozen=True)
class ShownResult:
    mode: Mode
    request: str
    formatted: FormattedAnswer
    sessions: tuple[Any, ...]


def init_state() -> None:
    st.session_state.setdefault("last_result", None)


def clear_result() -> None:
    st.session_state.last_result = None


def render_modes(
    config: AppConfig,
    service: ResearchService,
    writer: AcademicWriter,
    llm_ok: bool,
    run: RunAsync,
) -> None:
    st.subheader("3. Pergunta, resumo ou texto")
    mode = st.radio(
        "O que você quer?", options=list(Mode), format_func=_MODE_LABELS.get, horizontal=True
    )
    has_docs = service.has_documents()
    if not has_docs:
        st.info("O acervo está vazio. Envie ou baixe documentos acima.")
    if mode is Mode.QUESTION:
        _question(config, service, llm_ok and has_docs, run)
    elif mode is Mode.SUMMARY:
        _summary(config, service, writer, llm_ok and has_docs, run)
    else:
        _academic_text(config, writer, llm_ok and has_docs, run)


def _question(config: AppConfig, service: ResearchService, enabled: bool, run: RunAsync) -> None:
    question = st.text_input(
        "Pergunte sobre o seu acervo",
        placeholder="Ex.: Quais são as principais conclusões sobre avaliação formativa?",
    )
    if st.button("Perguntar", type="primary", disabled=not (enabled and question.strip())):
        _execute(config, Mode.QUESTION, question, lambda: service.ask(question, config.answer_language), run)


def _summary(
    config: AppConfig, service: ResearchService, writer: AcademicWriter, enabled: bool, run: RunAsync
) -> None:
    names = [e.docname for _, e in service.list_entries()]
    docname = st.selectbox("Documento a resumir", options=names, disabled=not names)
    st.caption("O resumo usa só trechos deste documento: objetivo, método, resultados e conclusões.")
    if st.button("Resumir", type="primary", disabled=not (enabled and docname)):
        _execute(
            config, Mode.SUMMARY, f"Resumo de {docname}",
            lambda: writer.summarize_document(docname, config.answer_language), run,
        )


def _academic_text(config: AppConfig, writer: AcademicWriter, enabled: bool, run: RunAsync) -> None:
    theme = st.text_area(
        "Tema e objetivo do texto",
        placeholder="Ex.: Avaliação formativa no ensino fundamental: conceitos e desafios.",
    )
    sections = st.text_area(
        "Seções (uma por linha)", value="\n".join(DEFAULT_SECTIONS), height=110,
        help="Cada seção é escrita com uma busca própria no acervo. Mais seções = mais tempo.",
    )
    st.caption("Cada seção leva o tempo de uma pergunta. Com IA local, pode levar vários minutos.")
    if st.button("Escrever texto", type="primary", disabled=not (enabled and theme.strip())):
        _write_sections(config, writer, theme, sections, run)


def _write_sections(
    config: AppConfig, writer: AcademicWriter, theme: str, sections_raw: str, run: RunAsync
) -> None:
    """Uma chamada por seção, para mostrar o progresso na tela.

    O progresso é escrito aqui, na thread do Streamlit: a IA roda em outra
    thread (BackgroundLoop), onde `st.write` não funciona.
    """
    try:
        theme, sections = writer.plan_text(theme, sections_raw)
    except WritingInputError as exc:
        st.warning(str(exc))
        return
    with st.status(f"Escrevendo {len(sections)} seções com `{config.llm_model}`…", expanded=True) as status:
        written = []
        try:
            for i, title in enumerate(sections, start=1):
                st.write(f"Seção {i} de {len(sections)}: {title}…")
                written.append(run(writer.write_section(theme, title, sections, config.answer_language)))
        except Exception as exc:  # noqa: BLE001 (erros do PaperQA/LiteLLM são variados)
            status.update(label="Erro ao escrever o texto", state="error")
            st.error(f"Falha na seção {len(written) + 1}: {exc}")
            if not written:
                return
            st.info("As seções já escritas foram mantidas abaixo.")
        text = writer.assemble(theme, written)
        st.session_state.last_result = ShownResult(
            Mode.ACADEMIC_TEXT, theme, text.combined, tuple(w.result.session for w in text.sections)
        )
        if len(written) == len(sections):
            status.update(label="Texto pronto", state="complete")


def _execute(config: AppConfig, mode: Mode, request: str, make_coro, run: RunAsync) -> None:
    with st.status(f"Processando com `{config.llm_model}`…", expanded=True) as status:
        try:
            outcome = run(make_coro())
        except (QuestionError, WritingInputError) as exc:
            status.update(label="Pedido inválido", state="error")
            st.warning(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 (erros do PaperQA/LiteLLM são variados)
            clear_result()
            status.update(label="Erro na consulta", state="error")
            st.error(f"Falha: {exc}")
            return
        st.session_state.last_result = ShownResult(mode, request, outcome.formatted, (outcome.session,))
        status.update(label="Pronto", state="complete")


def render_result(config: AppConfig) -> None:
    shown: ShownResult | None = st.session_state.get("last_result")
    if shown is None:
        return
    st.subheader("4. Resultado")
    formatted = shown.formatted
    st.markdown(formatted.text)
    if formatted.references:
        st.markdown("#### REFERÊNCIAS")
        for ref in formatted.references:
            st.markdown(ref)
    if formatted.missing_docnames:
        st.warning(
            "Sem dados ABNT: " + ", ".join(formatted.missing_docnames)
            + ". Preencha em *Dados da referência (ABNT)* e gere de novo."
        )
    st.download_button(
        "Baixar (.md)",
        data=document_to_markdown(
            _TITLES[shown.mode], shown.request, formatted.text, formatted.references,
            model=config.llm_name, generated_at=datetime.now(),
            missing_docnames=formatted.missing_docnames,
        ),
        file_name=f"{shown.mode.value}-ipeia-academico.md",
        mime="text/markdown",
    )
    with st.expander("Mostrar fontes (trechos usados)", expanded=False):
        _render_contexts(shown.sessions)


def _render_contexts(sessions: tuple[Any, ...]) -> None:
    contexts = [c for s in sessions for c in (getattr(s, "contexts", None) or [])]
    if not contexts:
        st.markdown("Nenhum trecho retornado.")
    for i, ctx in enumerate(contexts, start=1):
        text = getattr(ctx, "text", None)
        score = format_score(getattr(ctx, "score", None))
        st.markdown(f"**Trecho {i}**" + (f" (relevância: {score})" if score else ""))
        name = getattr(text, "name", "")
        if name:
            st.caption(name)
        st.write(getattr(ctx, "context", "") or getattr(text, "text", ""))
        st.divider()
