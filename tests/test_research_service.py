import asyncio

import pytest

from ipeia_academico.library import LibraryRepository
from ipeia_academico.research_service import (
    IndexOutcome,
    QuestionError,
    ResearchService,
    build_question,
)

PDF = b"%PDF-1.4 teste"


class FakeDocs:
    def __init__(self, docname="Silva 2024", fail=False):
        self.docname = docname
        self.fail = fail
        self.added = []
        self.queries = []

    async def aadd(self, path, settings=None):
        if self.fail:
            raise RuntimeError("Ollama caiu")
        self.added.append(path)
        return self.docname

    async def aquery(self, question, settings=None):
        self.queries.append(question)
        return f"resposta para: {question}"


def make_service(tmp_path, docs):
    repo = LibraryRepository(tmp_path / "acervo", tmp_path / "docs", FakeDocs)
    return ResearchService(repo, docs, settings="SETTINGS"), repo


def test_add_document_persiste_manifesto_e_docs(tmp_path):
    docs = FakeDocs()
    service, repo = make_service(tmp_path, docs)
    stored = service.store_file("a.pdf", PDF)

    result = asyncio.run(service.add_document(stored.path, stored.sha256, source="upload"))

    assert result.outcome is IndexOutcome.ADDED
    assert result.docname == "Silva 2024"
    assert service.is_indexed(stored.sha256)
    assert repo.docs_path.exists()
    assert [e.docname for e in service.list_documents()] == ["Silva 2024"]


def test_add_document_duplicado_nao_reindexa(tmp_path):
    docs = FakeDocs()
    service, _ = make_service(tmp_path, docs)
    stored = service.store_file("a.pdf", PDF)
    asyncio.run(service.add_document(stored.path, stored.sha256, source="upload"))

    again = asyncio.run(service.add_document(stored.path, stored.sha256, source="upload"))

    assert again.outcome is IndexOutcome.ALREADY_INDEXED
    assert len(docs.added) == 1


def test_add_document_quando_paperqa_ja_tem_o_conteudo(tmp_path):
    service, _ = make_service(tmp_path, FakeDocs(docname=None))
    stored = service.store_file("a.pdf", PDF)
    result = asyncio.run(service.add_document(stored.path, stored.sha256, source="upload"))
    assert result.outcome is IndexOutcome.ALREADY_INDEXED
    assert not service.has_documents()


def test_falha_na_indexacao_remove_arquivo_e_nao_persiste(tmp_path):
    service, repo = make_service(tmp_path, FakeDocs(fail=True))
    stored = service.store_file("a.pdf", PDF)

    with pytest.raises(RuntimeError, match="Ollama caiu"):
        asyncio.run(service.add_document(stored.path, stored.sha256, source="upload"))

    assert not stored.path.exists()
    assert not repo.manifest_path.exists()
    assert not service.has_documents()


def test_ask_com_acervo_vazio_e_bloqueado(tmp_path):
    service, _ = make_service(tmp_path, FakeDocs())
    with pytest.raises(QuestionError, match="vazio"):
        asyncio.run(service.ask("Qual a conclusão?", "português"))


def test_ask_envia_pergunta_com_idioma(tmp_path):
    docs = FakeDocs()
    service, _ = make_service(tmp_path, docs)
    stored = service.store_file("a.pdf", PDF)
    asyncio.run(service.add_document(stored.path, stored.sha256, source="upload"))

    asyncio.run(service.ask("  Qual   a conclusão? ", "português do Brasil"))

    assert docs.queries == ["Qual a conclusão?\n\n(Responda em português do Brasil.)"]


def test_reset_library(tmp_path):
    service, _ = make_service(tmp_path, FakeDocs())
    stored = service.store_file("a.pdf", PDF)
    asyncio.run(service.add_document(stored.path, stored.sha256, source="upload"))
    service.reset_library()
    assert not service.has_documents()


@pytest.mark.parametrize("bad", ["", "  ", "ab", "x" * 2001])
def test_build_question_rejeita_invalidas(bad):
    with pytest.raises(QuestionError):
        build_question(bad, "português")


def test_build_question_sem_idioma():
    assert build_question("O que é RAG?", "") == "O que é RAG?"
