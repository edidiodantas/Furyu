"""Regra de negócio: indexar documentos no acervo e responder perguntas.

Não conhece Streamlit nem rede. Recebe o repositório, o objeto `Docs` e as
`Settings` por injeção, o que permite testar com dublês.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ipeia_academico.library import LibraryRepository, ManifestEntry, StoredFile

MIN_QUESTION_CHARS = 3
MAX_QUESTION_CHARS = 2000


class IndexOutcome(str, Enum):
    ADDED = "added"
    ALREADY_INDEXED = "already_indexed"


@dataclass(frozen=True)
class IndexResult:
    outcome: IndexOutcome
    filename: str
    docname: str


class QuestionError(ValueError):
    """Pergunta vazia, curta ou longa demais."""


def build_question(question: str, language: str) -> str:
    """Valida a pergunta e acrescenta a instrução de idioma.

    Os prompts internos do PaperQA2 são em inglês; sem a instrução, modelos
    pequenos tendem a responder em inglês. Fica no fim para pesar pouco na
    busca por similaridade.
    """
    q = " ".join((question or "").split())
    if len(q) < MIN_QUESTION_CHARS:
        raise QuestionError("Digite uma pergunta com pelo menos 3 caracteres.")
    if len(q) > MAX_QUESTION_CHARS:
        raise QuestionError(f"Pergunta longa demais (máximo {MAX_QUESTION_CHARS} caracteres).")
    if language:
        q = f"{q}\n\n(Responda em {language}.)"
    return q


class ResearchService:
    def __init__(self, repository: LibraryRepository, docs: Any, settings: Any) -> None:
        self._repo = repository
        self._docs = docs
        self._settings = settings

    @property
    def docs(self) -> Any:
        return self._docs

    def list_documents(self) -> list[ManifestEntry]:
        return sorted(self._repo.load_manifest().values(), key=lambda e: e.added_at)

    def has_documents(self) -> bool:
        return bool(self._repo.load_manifest())

    def is_indexed(self, sha256: str) -> bool:
        return sha256 in self._repo.load_manifest()

    def store_file(self, original_name: str, data: bytes) -> StoredFile:
        """Valida e grava o arquivo no acervo (sem indexar)."""
        return self._repo.store_file(original_name, data)

    async def add_document(self, path: Path, sha256: str, *, source: str) -> IndexResult:
        """Indexa um arquivo já gravado. Persistência só após sucesso.

        Se a indexação falhar, o arquivo recém-gravado é apagado para não
        deixar lixo em documentos/ nem duplicar o nome no próximo envio.
        """
        manifest = self._repo.load_manifest()
        if sha256 in manifest:
            entry = manifest[sha256]
            return IndexResult(IndexOutcome.ALREADY_INDEXED, entry.filename, entry.docname)

        try:
            docname = await self._docs.aadd(str(path), settings=self._settings)
        except Exception:
            path.unlink(missing_ok=True)
            raise

        # aadd devolve None quando o PaperQA2 já tem o mesmo conteúdo (dockey).
        if docname is None:
            return IndexResult(IndexOutcome.ALREADY_INDEXED, path.name, "")

        manifest[sha256] = self._repo.new_entry(path.name, docname, source)
        self._repo.save_docs(self._docs)
        self._repo.save_manifest(manifest)
        return IndexResult(IndexOutcome.ADDED, path.name, docname)

    async def ask(self, question: str, language: str) -> Any:
        if not self.has_documents():
            raise QuestionError("O acervo está vazio. Envie ou baixe documentos primeiro.")
        return await self._docs.aquery(build_question(question, language), settings=self._settings)

    def reset_library(self) -> None:
        self._docs = self._repo.reset()
