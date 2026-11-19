import json
from datetime import datetime, timezone

import pytest

from ipeia_academico.library import (
    InvalidDocumentError,
    LibraryError,
    LibraryRepository,
    sanitize_filename,
    sha256_bytes,
    unique_path,
    validate_document,
)

PDF = b"%PDF-1.4\n conteudo de teste"


class FakeDocs:
    """Dublê picklable do paperqa.Docs."""

    def __init__(self):
        self.items = []


@pytest.fixture
def repo(tmp_path):
    fixed = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    return LibraryRepository(tmp_path / "acervo", tmp_path / "docs", FakeDocs, clock=lambda: fixed)


# --- funções puras ----------------------------------------------------------
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Artigo Final.pdf", "Artigo_Final.pdf"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\x\\livro.PDF", "livro.pdf"),
        ("Educação & Inclusão (2024).pdf", "Educacao_Inclusao_2024.pdf"),
        ("", "documento"),
        ("....pdf", "documento.pdf"),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


def test_unique_path_gera_sufixo_numerico(tmp_path):
    existing = {tmp_path / "a.pdf", tmp_path / "a_2.pdf"}
    assert unique_path(tmp_path, "a.pdf", lambda p: p in existing) == tmp_path / "a_3.pdf"


def test_validate_aceita_pdf_e_txt():
    validate_document("x.pdf", PDF)
    validate_document("notas.md", b"# titulo")


@pytest.mark.parametrize(
    "name, data",
    [
        ("x.exe", b"MZ"),
        ("x.pdf", b"<html>nao e pdf</html>"),
        ("x.pdf", b""),
        ("sem_extensao", b"abc"),
    ],
)
def test_validate_rejeita(name, data):
    with pytest.raises(InvalidDocumentError):
        validate_document(name, data)


def test_validate_rejeita_arquivo_grande():
    with pytest.raises(InvalidDocumentError, match="limite"):
        validate_document("x.txt", b"a" * 11, max_bytes=10)


# --- repositório --------------------------------------------------------------
def test_store_file_nao_sobrescreve_nome_igual(repo):
    a = repo.store_file("artigo.pdf", PDF + b"A")
    b = repo.store_file("artigo.pdf", PDF + b"B")
    assert a.path.name == "artigo.pdf"
    assert b.path.name == "artigo_2.pdf"
    assert a.path.read_bytes() != b.path.read_bytes()


def test_store_file_reaproveita_arquivo_ja_indexado(repo):
    first = repo.store_file("artigo.pdf", PDF)
    repo.save_manifest({first.sha256: repo.new_entry(first.path.name, "Autor 2024", "upload")})
    again = repo.store_file("copia.pdf", PDF)
    assert again.path == first.path
    assert not (repo.documents_dir / "copia.pdf").exists()


def test_manifesto_ida_e_volta(repo):
    entry = repo.new_entry("a.pdf", "Silva 2020", "upload")
    repo.save_manifest({"abc": entry})
    loaded = repo.load_manifest()
    assert loaded == {"abc": entry}
    assert loaded["abc"].added_at == "2026-11-19T12:00:00+00:00"


def test_manifesto_corrompido_levanta_library_error(repo):
    repo.manifest_path.parent.mkdir(parents=True)
    repo.manifest_path.write_text("{quebrado", encoding="utf-8")
    with pytest.raises(LibraryError):
        repo.load_manifest()


def test_docs_persistem_entre_instancias(repo, tmp_path):
    docs = repo.load_docs()
    assert isinstance(docs, FakeDocs)
    docs.items.append("chunk")
    repo.save_docs(docs)

    other = LibraryRepository(repo.library_dir, repo.documents_dir, FakeDocs)
    assert other.load_docs().items == ["chunk"]


def test_docs_corrompido_levanta_library_error(repo):
    repo.docs_path.parent.mkdir(parents=True)
    repo.docs_path.write_bytes(b"nao e pickle")
    with pytest.raises(LibraryError, match="ilegível"):
        repo.load_docs()


def test_reset_apaga_indice_mas_mantem_arquivos(repo):
    stored = repo.store_file("a.pdf", PDF)
    repo.save_docs(FakeDocs())
    repo.save_manifest({stored.sha256: repo.new_entry("a.pdf", "x", "upload")})
    fresh = repo.reset()
    assert isinstance(fresh, FakeDocs)
    assert not repo.docs_path.exists()
    assert not repo.manifest_path.exists()
    assert stored.path.exists()


def test_gravacao_atomica_nao_deixa_temporarios(repo):
    repo.save_manifest({})
    leftovers = [p for p in repo.library_dir.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []
    assert json.loads(repo.manifest_path.read_text()) == {}


def test_sha256_bytes():
    assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_troca_de_embedding_exige_reindexar(tmp_path):
    a = LibraryRepository(tmp_path / "acervo", tmp_path / "docs", FakeDocs, embedding_model="st-A")
    a.save_docs(FakeDocs())
    b = LibraryRepository(tmp_path / "acervo", tmp_path / "docs", FakeDocs, embedding_model="st-B")
    with pytest.raises(LibraryError, match="reindexe"):
        b.load_docs()
    # mesmo modelo continua abrindo
    assert isinstance(a.load_docs(), FakeDocs)


def test_reset_apaga_meta(tmp_path):
    repo = LibraryRepository(tmp_path / "acervo", tmp_path / "docs", FakeDocs, embedding_model="st-A")
    repo.save_docs(FakeDocs())
    repo.reset()
    assert not repo.meta_path.exists()
