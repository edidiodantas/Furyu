from types import SimpleNamespace as NS

import pytest

from ipeia_academico.abnt import build_reference
from ipeia_academico.citations import (
    MISSING_DATA_NOTE,
    FormattedAnswer,
    format_answer,
    merge_references,
    pages_from_text_name,
    sources_from_contexts,
)

FREIRE = build_reference({
    "doc_type": "livro", "title": "Pedagogia do oprimido", "year": "1987", "authors": "Freire, Paulo",
    "place": "Rio de Janeiro", "publisher": "Paz e Terra",
})


def ctx(key, name, docname, citation="Citação do PaperQA"):
    doc = NS(docname=docname, formatted_citation=citation)
    return NS(id=key, text=NS(name=name, doc=doc))


SOURCES = sources_from_contexts([
    ctx("pqac-11111111", "Freire1987 pages 45-46", "Freire1987"),
    ctx("pqac-22222222", "Freire1987 pages 50-50", "Freire1987"),
    ctx("pqac-33333333", "Notas chunk 2", "Notas", "Fulano, Notas, 2021"),
])


@pytest.mark.parametrize(
    ("name", "pages"),
    [("X pages 3-4", "3-4"), ("X pages 12-12", "12"), ("X chunk 2", ""), ("", ""), ("X page 7", "7")],
)
def test_pages_from_text_name(name, pages):
    assert pages_from_text_name(name) == pages


def test_sources_ignora_contextos_incompletos():
    assert sources_from_contexts([NS(id="", text=None), NS(id="k", text=NS(name="a", doc=None))]) == {}


def test_troca_chave_por_citacao_abnt():
    out = format_answer("Educar é libertar (pqac-11111111).", SOURCES, {"Freire1987": FREIRE})
    assert out.text == "Educar é libertar (Freire, 1987, p. 45-46)."
    assert out.references == (
        "FREIRE, Paulo. **Pedagogia do oprimido**. Rio de Janeiro: Paz e Terra, 1987.",
    )
    assert out.missing_docnames == ()


def test_varias_chaves_no_mesmo_parenteses_e_caixa_alta():
    out = format_answer(
        "Texto (pqac-11111111, pqac-22222222).", SOURCES, {"Freire1987": FREIRE}, uppercase=True
    )
    assert out.text == "Texto (FREIRE, 1987, p. 45-46; FREIRE, 1987, p. 50)."
    assert len(out.references) == 1


def test_documento_sem_dados_abnt_usa_fallback_e_avisa():
    out = format_answer("Ponto (pqac-33333333).", SOURCES, {})
    assert out.text == "Ponto (Notas)."
    assert out.references == (f"Fulano, Notas, 2021 {MISSING_DATA_NOTE}",)
    assert out.missing_docnames == ("Notas",)


def test_remove_chave_inventada_e_trata_chave_solta():
    out = format_answer("A (pqac-99999999). B pqac-11111111 .", SOURCES, {"Freire1987": FREIRE})
    assert out.text == "A. B (Freire, 1987, p. 45-46)."


def test_resposta_sem_citacoes():
    out = format_answer("Não é possível responder com base no acervo.", SOURCES, {})
    assert out.references == () and out.missing_docnames == ()


def test_merge_references_sem_repeticao_e_em_ordem():
    a = FormattedAnswer("A", ("ZETA.", "ALFA."), ("x",))
    b = FormattedAnswer("B", ("ALFA.",), ("x", "y"))
    merged = merge_references([a, b])
    assert merged.text == "A\n\nB"
    assert merged.references == ("ALFA.", "ZETA.")
    assert merged.missing_docnames == ("x", "y")
