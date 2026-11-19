"""Integração: o `Docs` real do PaperQA2 sobrevive ao ciclo salvar/carregar."""

import pytest

paperqa = pytest.importorskip("paperqa")

from ipeia_academico.library import LibraryRepository  # noqa: E402


def test_docs_real_ida_e_volta(tmp_path):
    repo = LibraryRepository(tmp_path / "acervo", tmp_path / "docs", paperqa.Docs)
    docs = repo.load_docs()
    assert isinstance(docs, paperqa.Docs)
    docs.name = "meu-acervo"
    repo.save_docs(docs)

    loaded = LibraryRepository(tmp_path / "acervo", tmp_path / "docs", paperqa.Docs).load_docs()
    assert isinstance(loaded, paperqa.Docs)
    assert loaded.name == "meu-acervo"
