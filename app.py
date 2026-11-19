"""IPeia Acadêmico: interface Streamlit (camada de entrada).

Só cuida de tela e de ligar as peças. Regra de negócio fica em
`ipeia_academico/research_service.py`; acesso a disco em `library.py`;
rede em `ipeia_academico/search/`.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from paperqa import Docs

from ipeia_academico.async_runner import BackgroundLoop
from ipeia_academico.config import AppConfig, ConfigError, load_config
from ipeia_academico.export import answer_to_markdown, extract_answer_text, extract_references
from ipeia_academico.library import (
    ALLOWED_EXTENSIONS,
    InvalidDocumentError,
    LibraryError,
    LibraryRepository,
    sha256_bytes,
)
from ipeia_academico.llm_settings import build_settings
from ipeia_academico.ollama_health import OllamaHealth, check_ollama
from ipeia_academico.research_service import IndexOutcome, QuestionError, ResearchService
from ipeia_academico.search import (
    SearchError,
    download_pdf,
    resolve_pdf_url,
    safe_pdf_filename,
    search_academic,
)
from ipeia_academico.ui_helpers import escape_markdown, format_score, hit_button_key

ROOT = Path(__file__).resolve().parent
APP_NAME = "IPeia Acadêmico"
# Logo oficial IPeia (obrigatória em todos os projetos).
LOGO_PATH = ROOT / "assets" / "logo-ipeia.png"
FAVICON_PATH = ROOT / "assets" / "favicon-ipeia.png"


# ---------------------------------------------------------------------------
# Inicialização (uma vez por processo)
# ---------------------------------------------------------------------------
def _bootstrap_config() -> AppConfig:
    load_dotenv(ROOT / ".env")
    # Evita fallback acidental para a API paga se a chave existir no shell.
    os.environ.pop("OPENAI_API_KEY", None)
    config = load_config(os.environ, ROOT)
    config.pdf_dir.mkdir(parents=True, exist_ok=True)
    config.pqa_home.mkdir(parents=True, exist_ok=True)
    os.environ["PQA_HOME"] = str(config.pqa_home.resolve())
    return config


@st.cache_resource
def get_loop() -> BackgroundLoop:
    return BackgroundLoop()


@st.cache_resource
def get_service(_config: AppConfig) -> ResearchService:
    """Um serviço por processo: o acervo é carregado do disco só uma vez."""
    repo = LibraryRepository(
        _config.library_dir, _config.pdf_dir, Docs, embedding_model=_config.embedding_model
    )
    return ResearchService(repo, repo.load_docs(), build_settings(_config))


@st.cache_data(ttl=30, show_spinner=False)
def get_ollama_health(base_url: str, model: str) -> OllamaHealth:
    # Cache de 30 s: antes a checagem rodava a cada clique e travava até 3 s
    # quando o Ollama estava desligado.
    return check_ollama(base_url, model)


def init_session_state() -> None:
    st.session_state.setdefault("search_hits", [])
    st.session_state.setdefault("search_note", "")
    st.session_state.setdefault("last_answer", None)
    st.session_state.setdefault("last_question", "")
    # Arquivos que falharam nesta sessão: não reprocessar a cada rerun.
    st.session_state.setdefault("failed_uploads", set())


# ---------------------------------------------------------------------------
# Seções da tela
# ---------------------------------------------------------------------------
def render_header(config: AppConfig, health: OllamaHealth) -> None:
    css = (ROOT / "assets" / "fonts.css").read_text(encoding="utf-8")
    st.html(
        f"""<style>
        {css}
        body {{ font-family: 'Ubuntu', sans-serif; }}
        [data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
        header[data-testid="stHeader"] {{ display: none !important; }}
        .block-container {{ padding-top: 1rem !important; padding-bottom: 0.5rem !important; }}
        .app-title {{ font-family: 'Ubuntu', sans-serif; font-weight: 700; font-size: 3.2rem;
                      color: #1f77b4; line-height: 1.1; margin: 0 0 .2rem 0; }}
        </style>"""
    )
    logo_col, title_col = st.columns([1, 6], vertical_alignment="center")
    with logo_col:
        st.image(str(LOGO_PATH), width=110)
    with title_col:
        st.markdown(f'<div class="app-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.caption("Pesquisa, leitura e escrita acadêmica com IA local, a partir do seu acervo.")
    st.caption(
        f"Modelo: `{config.ollama_model}` · Embeddings: `{config.embedding_model}` · "
        f"Ollama: `{config.ollama_base_url}`"
    )
    (st.success if health.ok else st.error)(health.message)


def render_sidebar(config: AppConfig, service: ResearchService) -> None:
    with st.sidebar:
        st.header("Acervo")
        docs = service.list_documents()
        st.caption(f"{len(docs)} documento(s) indexado(s), salvos em disco.")
        with st.expander("Ver documentos", expanded=False):
            for entry in docs:
                st.markdown(f"- **{escape_markdown(entry.docname)}**  \n  `{entry.filename}`")
        st.markdown(
            f"- **LLM (4 papéis)**: `{config.llm_name}`\n"
            f"- **Arquivos**: `{config.pdf_dir}`\n"
            f"- **Índice**: `{config.library_dir}`\n"
            f"- **Idioma das respostas**: {config.answer_language}"
        )
        st.warning("A primeira resposta pode levar minutos (carga do modelo). Não feche a aba.")

        if st.button("Limpar resposta", use_container_width=True):
            st.session_state.last_answer = None
            st.session_state.search_hits = []
            st.session_state.search_note = ""
            st.rerun()

        st.divider()
        confirm = st.checkbox("Quero apagar o índice do acervo")
        if st.button("Apagar índice", type="secondary", disabled=not confirm, use_container_width=True):
            service.reset_library()
            st.session_state.last_answer = None
            st.success("Índice apagado. Os arquivos em documentos/ continuam no disco.")
            st.rerun()


def _index_file(service: ResearchService, path: Path, digest: str, source: str) -> None:
    result = get_loop().run(service.add_document(path, digest, source=source))
    if result.outcome is IndexOutcome.ALREADY_INDEXED:
        st.info(f"Já estava no acervo: {result.filename}")
    else:
        st.success(f"Indexado: {result.docname or result.filename}")


def render_upload(service: ResearchService, ollama_ok: bool) -> None:
    st.subheader("1. Enviar documentos (artigos e livros)")
    exts = [e.lstrip(".") for e in ALLOWED_EXTENSIONS]
    uploaded = st.file_uploader(
        f"Selecione arquivos ({', '.join(exts)})",
        type=exts,
        accept_multiple_files=True,
        help="Os arquivos ficam no seu computador e o índice é salvo em disco.",
        disabled=not ollama_ok,
    )
    for f in uploaded or []:
        data = f.getvalue()
        digest = sha256_bytes(data)
        if digest in st.session_state.failed_uploads or service.is_indexed(digest):
            continue  # Streamlit reenvia a lista a cada rerun; só processa o que é novo
        with st.status(f"Processando `{f.name}`… (pode demorar)", expanded=True) as status:
            try:
                stored = service.store_file(f.name, data)
                st.write("Extraindo texto, gerando embeddings e metadados…")
                _index_file(service, stored.path, stored.sha256, source="upload")
                status.update(label=f"Pronto: {f.name}", state="complete")
            except (InvalidDocumentError, LibraryError) as exc:
                st.session_state.failed_uploads.add(digest)
                status.update(label=f"Rejeitado: {f.name}", state="error")
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001 (erros do PaperQA/LiteLLM são variados)
                st.session_state.failed_uploads.add(digest)
                status.update(label=f"Erro ao indexar {f.name}", state="error")
                st.error(f"Falha: {exc}")


def render_search(config: AppConfig, service: ResearchService, ollama_ok: bool) -> None:
    st.subheader("2. Buscar artigos (acesso aberto)")
    st.caption(
        "Sem login. Começa no **Oasisbr (IBICT)**; se não houver resultado, usa "
        "Semantic Scholar e Crossref. Unpaywall só para achar PDF **aberto**. Paywall não é baixado."
    )
    query = st.text_input("Tema ou título", placeholder="Ex.: educação inclusiva Brasil")
    clicked = st.button("Buscar", type="secondary")
    if not config.contact_email:
        st.caption("Dica: defina um e-mail real em CONTACT_EMAIL no `.env` para o Unpaywall achar mais PDFs.")

    if clicked:
        if not query.strip():
            st.warning("Digite um tema para buscar.")
        else:
            with st.spinner("Consultando catálogos…"):
                try:
                    hits, note = search_academic(
                        query, s2_key=config.semantic_scholar_key, email=config.contact_email
                    )
                    st.session_state.search_hits, st.session_state.search_note = hits, note
                except SearchError as exc:
                    st.session_state.search_hits, st.session_state.search_note = [], ""
                    st.error(str(exc))
            if not st.session_state.search_hits:
                st.info("Nenhum artigo encontrado. Tente outras palavras.")

    hits = st.session_state.search_hits
    if not hits:
        return
    n_open = sum(1 for h in hits if h.has_open_pdf)
    st.write(f"{len(hits)} resultado(s) via {st.session_state.search_note} · {n_open} com PDF aberto:")
    for i, hit in enumerate(hits):
        with st.container(border=True):
            st.markdown(f"**{escape_markdown(hit.title)}** ({hit.year or '?'})")
            if hit.authors:
                st.caption(hit.authors)
            extra = " · ".join(x for x in (hit.venue, hit.source) if x)
            if extra:
                st.caption(extra)
            if hit.doi:
                st.caption(f"DOI: {hit.doi}")
            if hit.abstract:
                st.write(hit.abstract)
            if not hit.has_open_pdf:
                st.caption("Sem PDF aberto. Baixe no site da revista e use Enviar documentos.")
            if st.button(
                "Baixar PDF aberto e indexar",
                key=hit_button_key(i, hit),
                disabled=not (ollama_ok and hit.has_open_pdf),
            ):
                _download_and_index(config, service, hit)


def _download_and_index(config: AppConfig, service: ResearchService, hit) -> None:
    with st.status("Obtendo PDF…", expanded=True) as status:
        try:
            url = resolve_pdf_url(hit, config.contact_email)
            if not url:
                raise RuntimeError("Sem PDF em acesso aberto. Baixe no site da revista.")
            path = download_pdf(url, config.pdf_dir, safe_pdf_filename(hit.title, hit.year))
            digest = sha256_bytes(path.read_bytes())
            if service.is_indexed(digest):
                path.unlink(missing_ok=True)  # mesmo conteúdo já está no acervo
                status.update(label="Este PDF já está no acervo", state="complete")
                return
            st.write("Indexando com o Ollama (pode demorar)…")
            _index_file(service, path, digest, source=f"download:{url}")
            status.update(label=f"Indexado: {path.name}", state="complete")
        except Exception as exc:  # noqa: BLE001
            status.update(label="Não foi possível indexar", state="error")
            st.error(str(exc))


def render_question(config: AppConfig, service: ResearchService, ollama_ok: bool) -> None:
    st.subheader("3. Pergunta")
    question = st.text_input(
        "Pergunte sobre o seu acervo",
        placeholder="Ex.: Quais são as principais conclusões sobre avaliação formativa?",
    )
    has_docs = service.has_documents()
    if not has_docs:
        st.info("O acervo está vazio. Envie ou baixe documentos acima.")
    if not st.button("Perguntar", type="primary", disabled=not (has_docs and question.strip() and ollama_ok)):
        return
    with st.status(f"Processando com `{config.ollama_model}`… (1 a 3 minutos)", expanded=True) as status:
        try:
            st.session_state.last_answer = get_loop().run(service.ask(question, config.answer_language))
            st.session_state.last_question = question.strip()
            status.update(label="Resposta pronta", state="complete")
        except QuestionError as exc:
            status.update(label="Pergunta inválida", state="error")
            st.warning(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.session_state.last_answer = None
            status.update(label="Erro na consulta", state="error")
            st.error(f"Falha: {exc}")


def render_answer(config: AppConfig) -> None:
    session = st.session_state.last_answer
    if session is None:
        return
    st.subheader("4. Resposta")
    answer = extract_answer_text(session)
    references = extract_references(session)
    st.markdown(answer)
    st.download_button(
        "Baixar resposta (.md)",
        data=answer_to_markdown(
            st.session_state.last_question,
            answer,
            references,
            model=config.ollama_model,
            generated_at=datetime.now(),
        ),
        file_name="resposta-ipeia-academico.md",
        mime="text/markdown",
    )
    with st.expander("Mostrar fontes (trechos usados)", expanded=False):
        contexts = getattr(session, "contexts", None) or []
        if not contexts:
            st.markdown(references or "Nenhuma fonte estruturada retornada.")
        for i, ctx in enumerate(contexts, start=1):
            text = getattr(ctx, "text", None)
            doc = getattr(text, "doc", None)
            citation = (
                getattr(doc, "citation", "") or getattr(doc, "docname", "") or getattr(text, "name", "")
            )
            score = format_score(getattr(ctx, "score", None))
            st.markdown(f"**Fonte {i}**" + (f" (relevância: {score})" if score else ""))
            if citation:
                st.caption(citation)
            st.write(getattr(ctx, "context", "") or getattr(text, "text", ""))
            st.divider()


def render_broken_library(config: AppConfig, exc: LibraryError) -> None:
    """Acervo ilegível: oferece apagar o índice sem precisar mexer em pastas."""
    st.error(str(exc))
    if st.checkbox("Entendi: apagar o índice (os arquivos em documentos/ ficam)"):
        if st.button("Apagar índice e recomeçar", type="primary"):
            LibraryRepository(config.library_dir, config.pdf_dir, Docs).reset()
            get_service.clear()
            st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon=str(FAVICON_PATH),
        layout="wide",
        menu_items={
            "Get help": None,
            "Report a bug": None,
            "About": f"{APP_NAME}: pesquisa acadêmica com IA local.",
        },
    )
    st.logo(str(LOGO_PATH), size="large")
    try:
        config = _bootstrap_config()
    except ConfigError as exc:
        st.error(f"Erro no .env: {exc}")
        st.stop()

    init_session_state()
    health = get_ollama_health(config.ollama_base_url, config.ollama_model)
    render_header(config, health)

    try:
        service = get_service(config)
    except LibraryError as exc:
        render_broken_library(config, exc)
        st.stop()

    render_sidebar(config, service)
    render_upload(service, health.ok)
    render_search(config, service, health.ok)
    render_question(config, service, health.ok)
    render_answer(config)


main()
