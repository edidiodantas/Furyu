"""Regra de negócio: indexar documentos no acervo e responder perguntas.

Não conhece Streamlit nem rede. Recebe o repositório, o objeto `Docs` e as
`Settings` por injeção, o que permite testar com dublês.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ipeia_academico.abnt import BibReference, BibReferenceError, build_reference
from ipeia_academico.citations import FormattedAnswer, format_answer, sources_from_contexts
from ipeia_academico.export import extract_answer_text
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


@dataclass(frozen=True)
class AnswerResult:
    """Sessão do PaperQA2 (trechos usados) + texto já com citações ABNT."""

    session: Any
    formatted: FormattedAnswer


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
    def __init__(
        self,
        repository: LibraryRepository,
        docs: Any,
        settings: Any,
        *,
        citation_uppercase: bool = False,
    ) -> None:
        self._repo = repository
        self._docs = docs
        self._settings = settings
        self._citation_uppercase = citation_uppercase

    @property
    def docs(self) -> Any:
        return self._docs

    def new_docs(self) -> Any:
        return self._repo.new_docs()

    def list_documents(self) -> list[ManifestEntry]:
        return sorted(self._repo.load_manifest().values(), key=lambda e: e.added_at)

    def list_entries(self) -> list[tuple[str, ManifestEntry]]:
        """(sha256, entrada) em ordem de inclusão; a chave identifica o arquivo."""
        return sorted(self._repo.load_manifest().items(), key=lambda kv: kv[1].added_at)

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

    async def ask(self, question: str, language: str, *, settings: Any = None) -> AnswerResult:
        if not self.has_documents():
            raise QuestionError("O acervo está vazio. Envie ou baixe documentos primeiro.")
        session = await self._docs.aquery(
            build_question(question, language), settings=settings or self._settings
        )
        return AnswerResult(session, self.format_session(session))

    # --- referências ABNT ---------------------------------------------------
    def set_reference(self, sha256: str, data: dict[str, Any]) -> BibReference:
        """Valida e grava os dados bibliográficos de um documento do acervo."""
        reference = build_reference(data)
        self._repo.set_reference(sha256, reference.to_dict())
        return reference

    def references_by_docname(self) -> dict[str, BibReference]:
        refs: dict[str, BibReference] = {}
        for entry in self._repo.load_manifest().values():
            if not entry.reference:
                continue
            try:
                refs[entry.docname] = build_reference(entry.reference)
            except BibReferenceError:
                continue  # dado antigo inválido: tratado como "sem dados ABNT"
        return refs

    def format_session(self, session: Any) -> FormattedAnswer:
        raw = getattr(session, "raw_answer", "") or extract_answer_text(session)
        return format_answer(
            raw,
            sources_from_contexts(getattr(session, "contexts", None) or []),
            self.references_by_docname(),
            uppercase=self._citation_uppercase,
        )

    def reset_library(self) -> None:
        self._docs = self._repo.reset()
