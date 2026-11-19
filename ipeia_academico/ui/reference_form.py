"""Formulário dos dados bibliográficos (ABNT) de cada documento do acervo."""

from __future__ import annotations

from datetime import date

import streamlit as st

from ipeia_academico.abnt import BibReferenceError, DocType, build_reference, format_reference
from ipeia_academico.library import LibraryError
from ipeia_academico.research_service import ResearchService

_TYPE_LABELS = {
    DocType.BOOK: "Livro",
    DocType.ARTICLE: "Artigo de periódico",
    DocType.ONLINE: "Documento on-line (site, relatório)",
}


def _status_label(entry) -> str:
    mark = "✓" if entry.reference else "•"
    return f"{mark} {entry.docname} ({entry.filename})"


def render_reference_form(service: ResearchService) -> None:
    entries = service.list_entries()
    with st.expander("Dados da referência (ABNT)", expanded=False):
        if not entries:
            st.caption("Envie documentos para preencher os dados bibliográficos.")
            return
        st.caption(
            "Preencha para que as citações saiam como (Silva, 2020, p. 15) e a lista de "
            "REFERÊNCIAS seja montada pelo app. ✓ = já preenchido. Sem estes dados, o "
            "app usa o nome interno do documento e marca a referência como incompleta."
        )
        labels = {sha: _status_label(e) for sha, e in entries}
        sha = st.selectbox("Documento", options=list(labels), format_func=labels.get, key="ref_doc")
        entry = dict(entries)[sha]
        current = entry.reference or {}

        doc_type = st.radio(
            "Tipo",
            options=list(DocType),
            format_func=_TYPE_LABELS.get,
            index=list(DocType).index(DocType(current.get("doc_type", DocType.BOOK.value))),
            horizontal=True,
            key=f"ref_type_{sha}",
        )
        with st.form(f"ref_form_{sha}"):
            data = _form_fields(doc_type, current)
            submitted = st.form_submit_button("Salvar referência", type="primary")
        if submitted:
            try:
                ref = service.set_reference(sha, {"doc_type": doc_type.value, **data})
                st.success("Referência salva.")
                st.markdown(format_reference(ref))
            except (BibReferenceError, LibraryError) as exc:
                st.error(str(exc))
        elif entry.reference:
            st.caption("Como está hoje:")
            try:
                st.markdown(format_reference(build_reference(entry.reference)))
            except BibReferenceError as exc:
                st.warning(f"Dados salvos incompletos: {exc}")


def _form_fields(doc_type: DocType, current: dict) -> dict:
    authors_default = "\n".join(current.get("authors") or [])
    data = {
        "authors": st.text_area(
            "Autores (um por linha, como Sobrenome, Nome)",
            value=authors_default,
            placeholder="Freire, Paulo\nSaviani, Dermeval",
            help="Também aceita 'Paulo Freire'. Deixe vazio para obra sem autor.",
        ),
        "title": st.text_input("Título", value=current.get("title", "")),
        "subtitle": st.text_input("Subtítulo (opcional)", value=current.get("subtitle", "")),
        "year": st.text_input("Ano", value=current.get("year", ""), max_chars=4),
    }
    if doc_type is DocType.BOOK:
        c1, c2, c3 = st.columns(3)
        data["edition"] = c1.text_input("Edição", value=current.get("edition", ""), placeholder="2")
        data["place"] = c2.text_input("Local", value=current.get("place", ""), placeholder="São Paulo")
        data["publisher"] = c3.text_input("Editora", value=current.get("publisher", ""))
    elif doc_type is DocType.ARTICLE:
        data["journal"] = st.text_input("Periódico", value=current.get("journal", ""))
        c1, c2, c3, c4 = st.columns(4)
        data["place"] = c1.text_input("Local (opcional)", value=current.get("place", ""))
        data["volume"] = c2.text_input("Volume", value=current.get("volume", ""))
        data["number"] = c3.text_input("Número", value=current.get("number", ""))
        data["pages"] = c4.text_input("Páginas", value=current.get("pages", ""), placeholder="10-25")
    data["doi"] = st.text_input("DOI (opcional)", value=current.get("doi", ""))
    data["url"] = st.text_input("Endereço on-line (opcional)", value=current.get("url", ""))
    accessed = st.date_input(
        "Acesso em (se tiver endereço on-line)",
        value=date.fromisoformat(current["accessed"]) if current.get("accessed") else None,
        format="DD/MM/YYYY",
    )
    data["accessed"] = accessed.isoformat() if accessed else ""
    return data
