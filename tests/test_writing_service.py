import asyncio
from types import SimpleNamespace as NS

import pytest

from ipeia_academico.academic_prompts import Mode, WritingInputError
from ipeia_academico.library import LibraryRepository
from ipeia_academico.research_service import ResearchService
from ipeia_academico.writing_service import AcademicWriter

PDF = b"%PDF-1.4 teste"


def make_ctx(key, docname):
    return NS(id=key, text=NS(name=f"{docname} pages 2-3", doc=NS(docname=docname, formatted_citation="c")))


class FakeDocs:
    """Imita o Docs do PaperQA2 no que o escritor usa."""

    def __init__(self):
        self.docs = {}
        self.texts = []
        self.queries = []
        self.settings_used = []
        self.added_texts = None

    def add(self, dockey, docname, n_texts):
        doc = NS(dockey=dockey, docname=docname)
        self.docs[dockey] = doc
        self.texts += [NS(doc=doc, text=f"t{i}") for i in range(n_texts)]

    async def aadd(self, path, settings=None):
        return "Freire1987"

    async def aadd_texts(self, texts, doc, settings=None):
        self.added_texts = (texts, doc)
        self.docs[doc.dockey] = doc
        return True

    async def aquery(self, question, settings=None):
        self.queries.append(question)
        self.settings_used.append(settings)
        return NS(raw_answer="Texto (pqac-aaaaaaaa).", contexts=[make_ctx("pqac-aaaaaaaa", "Freire1987")])


def setup(tmp_path, with_doc=True):
    main = FakeDocs()
    scoped = FakeDocs()
    repo = LibraryRepository(tmp_path / "acervo", tmp_path / "docs", lambda: scoped)
    service = ResearchService(repo, main, settings="BASE")
    writer = AcademicWriter(service, lambda mode: f"S-{mode.value}")
    if with_doc:
        stored = service.store_file("a.pdf", PDF)
        asyncio.run(service.add_document(stored.path, stored.sha256, source="upload"))
        service.set_reference(stored.sha256, {
            "doc_type": "livro", "title": "Pedagogia", "year": "1987", "authors": "Paulo Freire",
        })
        main.add("k1", "Freire1987", 3)
        main.add("k2", "Outro2020", 2)
    return writer, main, scoped


def test_resumo_restringe_trechos_ao_documento(tmp_path):
    writer, main, scoped = setup(tmp_path)

    result = asyncio.run(writer.summarize_document("Freire1987", "português"))

    texts, doc = scoped.added_texts
    assert doc.docname == "Freire1987" and len(texts) == 3
    assert main.queries == []  # a busca é feita só na coleção restrita
    assert scoped.settings_used == ["S-resumo"]
    assert result.formatted.text == "Texto (Freire, 1987, p. 2-3)."


def test_resumo_de_documento_inexistente(tmp_path):
    writer, _, _ = setup(tmp_path)
    with pytest.raises(WritingInputError, match="não está no índice"):
        asyncio.run(writer.summarize_document("Nada", "português"))


def test_texto_academico_uma_busca_por_secao_e_referencias_unicas(tmp_path):
    writer, main, _ = setup(tmp_path)

    text = asyncio.run(writer.write_text("Avaliação formativa na escola", "Introdução\nConclusão", "pt"))

    assert len(main.queries) == 2
    assert all(s == f"S-{Mode.ACADEMIC_TEXT.value}" for s in main.settings_used)
    assert text.combined.text.startswith("## Introdução\n\nTexto (Freire, 1987, p. 2-3).")
    assert "## Conclusão" in text.combined.text
    assert len(text.combined.references) == 1


def test_texto_academico_valida_antes_de_chamar_a_ia(tmp_path):
    writer, main, _ = setup(tmp_path)
    with pytest.raises(WritingInputError):
        asyncio.run(writer.write_text("curto", "", "pt"))
    assert main.queries == []


def test_texto_academico_com_acervo_vazio(tmp_path):
    writer, _, _ = setup(tmp_path, with_doc=False)
    with pytest.raises(WritingInputError, match="vazio"):
        writer.plan_text("Avaliação formativa na escola", "")
