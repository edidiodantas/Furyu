from datetime import date

import pytest

from ipeia_academico.abnt import (
    BibReferenceError,
    DocType,
    build_reference,
    citation_author_label,
    format_citation_inner,
    format_reference,
    normalize_author,
    parse_authors,
    prefill_from_catalog,
    reference_sort_key,
)


def livro(**over):
    data = {
        "doc_type": "livro", "title": "Pedagogia do oprimido", "year": "1987",
        "authors": "Paulo Freire", "edition": "17", "place": "Rio de Janeiro", "publisher": "Paz e Terra",
    }
    return build_reference({**data, **over})


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Paulo Freire", "Freire, Paulo"),
        ("Freire, Paulo", "Freire, Paulo"),
        ("  Dermeval   Saviani ", "Saviani, Dermeval"),
        ("Joaquim Silva Filho", "Silva Filho, Joaquim"),
        ("UNESCO", "UNESCO"),
        ("", ""),
    ],
)
def test_normalize_author(raw, expected):
    assert normalize_author(raw) == expected


def test_parse_authors_por_linha_e_ponto_e_virgula():
    expected = ("Freire, Paulo", "Silva, Ana", "Souza, B.")
    assert parse_authors("Freire, Paulo\nAna Silva; Souza, B.") == expected


def test_parse_authors_limite():
    with pytest.raises(BibReferenceError, match="máximo"):
        parse_authors("\n".join(f"Autor{i}, A" for i in range(31)))


def test_referencia_livro():
    assert format_reference(livro()) == (
        "FREIRE, Paulo. **Pedagogia do oprimido**. 17. ed. Rio de Janeiro: Paz e Terra, 1987."
    )


def test_livro_primeira_edicao_e_sem_local_editora():
    ref = livro(edition="1", place="", publisher="")
    assert format_reference(ref) == "FREIRE, Paulo. **Pedagogia do oprimido**. [S. l.]: [s. n.], 1987."


def test_livro_com_subtitulo():
    assert "**Pedagogia do oprimido**: um estudo." in format_reference(livro(subtitle="um estudo"))


def test_referencia_artigo_com_doi():
    ref = build_reference({
        "doc_type": "artigo", "title": "Avaliação formativa", "year": "2020",
        "authors": ["Silva, Ana", "Beto Souza"], "journal": "Revista X",
        "volume": "25", "number": "3", "pages": "10-25", "doi": "https://doi.org/10.1590/abc",
    })
    assert format_reference(ref) == (
        "SILVA, Ana; SOUZA, Beto. Avaliação formativa. **Revista X**, v. 25, n. 3, p. 10-25, 2020. "
        "DOI: 10.1590/abc."
    )


def test_referencia_online_sem_autor_entra_pelo_titulo():
    ref = build_reference({
        "doc_type": "online", "title": "Relatório anual", "year": "2023",
        "url": "https://x.org/r", "accessed": "2024-03-05",
    })
    assert format_reference(ref) == (
        "RELATÓRIO anual. 2023. Disponível em: https://x.org/r. Acesso em: 5 mar. 2024."
    )


@pytest.mark.parametrize(
    ("over", "msg"),
    [
        ({"title": " "}, "título"),
        ({"year": "87"}, "ano"),
        ({"year": "s.d."}, "ano"),
        ({"doc_type": "tese"}, "Tipo"),
        ({"doc_type": "artigo"}, "periódico"),
        ({"accessed": "05/03/2024"}, "acesso"),
        ({"url": "javascript:alert(1)"}, "URL"),
    ],
)
def test_build_reference_rejeita_invalidos(over, msg):
    with pytest.raises(BibReferenceError, match=msg):
        livro(**over)


def test_to_dict_ida_e_volta():
    ref = livro()
    assert build_reference(ref.to_dict()) == ref


@pytest.mark.parametrize(
    ("authors", "upper", "expected"),
    [
        ("Freire, Paulo", False, "Freire"),
        ("Freire, Paulo", True, "FREIRE"),
        ("Silva, A\nSouza, B", False, "Silva; Souza"),
        ("Silva, A\nSouza, B\nLima, C", False, "Silva; Souza; Lima"),
        ("Silva, A\nSouza, B\nLima, C\nReis, D", False, "Silva *et al.*"),
        ("", False, "Pedagogia"),
    ],
)
def test_citation_author_label(authors, upper, expected):
    assert citation_author_label(livro(authors=authors), uppercase=upper) == expected


def test_format_citation_inner_com_e_sem_pagina():
    assert format_citation_inner(livro(), "45-46") == "Freire, 1987, p. 45-46"
    assert format_citation_inner(livro()) == "Freire, 1987"


def test_reference_sort_key_ignora_markdown():
    assert reference_sort_key("**ABC**") == reference_sort_key("abc")


def test_prefill_crossref_aproveita_autores():
    data = prefill_from_catalog(
        title="T", year=2021, authors="Ana Silva, Beto Souza", venue="Revista", doi="10.1/x",
        url="https://pdf", names_are_given_first=True, today=date(2024, 1, 2),
    )
    assert data["authors"] == ["Silva, Ana", "Souza, Beto"]
    assert data["doc_type"] == DocType.ARTICLE.value
    assert data["url"] == "" and data["accessed"] == ""
    assert build_reference(data).journal == "Revista"


def test_prefill_oasisbr_deixa_autores_vazios_e_usa_online_sem_periodico():
    data = prefill_from_catalog(
        title="T", year=None, authors="Silva, Ana, Souza, Beto", venue="", doi="",
        url="https://pdf", names_are_given_first=False, today=date(2024, 1, 2),
    )
    assert data["authors"] == []
    assert data["doc_type"] == DocType.ONLINE.value
    assert data["accessed"] == "2024-01-02"
    with pytest.raises(BibReferenceError, match="ano"):
        build_reference(data)  # sem ano, você completa no formulário
