"""Acervo persistente: arquivos dos documentos + índice do PaperQA2 em disco.

Problema que isto resolve: na versão anterior o `Docs` vivia só em
`st.session_state`. Ao recarregar a página ou reabrir o app, todo o índice
(embeddings e metadados) era perdido e cada livro/artigo tinha de ser
reindexado, o que leva minutos por arquivo com LLM local.

Formato em disco (dentro de `library_dir`):
- docs.pkl ........ objeto `Docs` serializado com pickle (forma de salvar
                    documentada no README do PaperQA2: "Can I save or load?")
- manifest.json ... {sha256: {filename, docname, source, added_at}}
- meta.json ....... {embedding_model}: embeddings de modelos diferentes não
                    são comparáveis; trocar EMBEDDING_MODEL exige reindexar.

Segurança: pickle executa código ao carregar. Só carregue um docs.pkl criado
por este app na sua máquina; nunca um recebido de terceiros.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import re
import tempfile
import unicodedata
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Formatos que o PaperQA2 lê sem extras adicionais (conferido em paperqa/readers.py:
# .pdf via parser PyMuPDF; .txt/.html via parse_text; demais extensões caem no
# parse_text genérico, o que cobre .md). .docx exige o extra "office".
ALLOWED_EXTENSIONS = (".pdf", ".txt", ".md", ".html")
MAX_FILE_BYTES = 200 * 1024 * 1024  # livros escaneados podem ser grandes

DOCS_FILENAME = "docs.pkl"
MANIFEST_FILENAME = "manifest.json"
META_FILENAME = "meta.json"


class LibraryError(RuntimeError):
    """Falha ao ler ou gravar o acervo."""


class InvalidDocumentError(ValueError):
    """Arquivo rejeitado (extensão, tamanho ou conteúdo)."""


@dataclass(frozen=True)
class ManifestEntry:
    filename: str
    docname: str
    source: str
    added_at: str


@dataclass(frozen=True)
class StoredFile:
    path: Path
    sha256: str


# ---------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize_filename(name: str, *, max_stem: int = 80) -> str:
    """Nome seguro: sem diretórios, sem caracteres de controle ou separadores.

    Acentos são preservados como letras ASCII equivalentes para evitar
    problemas no Windows/exFAT.
    """
    base = re.split(r"[\\/]", name or "")[-1]
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    stem, dot, ext = base.rpartition(".")
    if not dot:
        stem, ext = base, ""
    stem = re.sub(r"[^\w\s-]", "", stem).strip()
    stem = re.sub(r"[\s-]+", "_", stem).strip("_.")[:max_stem] or "documento"
    ext = re.sub(r"[^a-zA-Z0-9]", "", ext).lower()
    return f"{stem}.{ext}" if ext else stem


def validate_document(filename: str, data: bytes, *, max_bytes: int = MAX_FILE_BYTES) -> None:
    """Valida extensão, tamanho e assinatura (PDF precisa começar com %PDF)."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EXTENSIONS)
        raise InvalidDocumentError(f"Formato {ext or '(sem extensão)'} não suportado. Use: {allowed}.")
    if not data:
        raise InvalidDocumentError(f"{filename}: arquivo vazio.")
    if len(data) > max_bytes:
        raise InvalidDocumentError(
            f"{filename}: {len(data) // (1024 * 1024)} MB passa do limite de "
            f"{max_bytes // (1024 * 1024)} MB."
        )
    if ext == ".pdf" and not data.lstrip()[:5].startswith(b"%PDF"):
        raise InvalidDocumentError(f"{filename}: o conteúdo não é um PDF válido.")


def unique_path(directory: Path, filename: str, exists: Callable[[Path], bool]) -> Path:
    """Primeiro caminho livre: nome.pdf, nome_2.pdf, nome_3.pdf..."""
    candidate = directory / filename
    stem, suffix = candidate.stem, candidate.suffix
    counter = 2
    while exists(candidate):
        candidate = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


# ---------------------------------------------------------------------------
# Repositório (I/O)
# ---------------------------------------------------------------------------
def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Grava num temporário e troca: um crash no meio não corrompe o acervo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class LibraryRepository:
    """Guarda arquivos, o `Docs` serializado e o manifesto."""

    def __init__(
        self,
        library_dir: Path,
        documents_dir: Path,
        docs_factory: Callable[[], Any],
        *,
        embedding_model: str = "",
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.library_dir = library_dir
        self.documents_dir = documents_dir
        self.embedding_model = embedding_model
        self._docs_factory = docs_factory
        self._clock = clock

    @property
    def docs_path(self) -> Path:
        return self.library_dir / DOCS_FILENAME

    @property
    def manifest_path(self) -> Path:
        return self.library_dir / MANIFEST_FILENAME

    @property
    def meta_path(self) -> Path:
        return self.library_dir / META_FILENAME

    # --- arquivos -----------------------------------------------------------
    def store_file(self, original_name: str, data: bytes) -> StoredFile:
        """Valida e grava o arquivo sem sobrescrever outro de mesmo nome."""
        filename = sanitize_filename(original_name)
        validate_document(filename, data)
        digest = sha256_bytes(data)

        existing = self.find_file_by_hash(digest)
        if existing is not None:
            return StoredFile(existing, digest)

        self.documents_dir.mkdir(parents=True, exist_ok=True)
        dest = unique_path(self.documents_dir, filename, Path.exists)
        try:
            _atomic_write_bytes(dest, data)
        except OSError as exc:
            raise LibraryError(f"Não foi possível gravar {dest}: {exc}") from exc
        return StoredFile(dest, digest)

    def find_file_by_hash(self, digest: str) -> Path | None:
        entry = self.load_manifest().get(digest)
        if entry is None:
            return None
        path = self.documents_dir / entry.filename
        return path if path.exists() else None

    # --- manifesto ----------------------------------------------------------
    def load_manifest(self) -> dict[str, ManifestEntry]:
        if not self.manifest_path.exists():
            return {}
        try:
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return {k: ManifestEntry(**v) for k, v in raw.items()}
        except (OSError, ValueError, TypeError) as exc:
            raise LibraryError(f"Manifesto do acervo ilegível ({self.manifest_path}): {exc}") from exc

    def save_manifest(self, manifest: dict[str, ManifestEntry]) -> None:
        payload = json.dumps(
            {k: asdict(v) for k, v in manifest.items()}, ensure_ascii=False, indent=2
        ).encode("utf-8")
        try:
            _atomic_write_bytes(self.manifest_path, payload)
        except OSError as exc:
            raise LibraryError(f"Não foi possível gravar o manifesto: {exc}") from exc

    def new_entry(self, filename: str, docname: str, source: str) -> ManifestEntry:
        return ManifestEntry(
            filename=filename,
            docname=docname,
            source=source,
            added_at=self._clock().isoformat(timespec="seconds"),
        )

    # --- índice (Docs) ------------------------------------------------------
    def _check_embedding_model(self) -> None:
        if not self.embedding_model or not self.meta_path.exists():
            return
        try:
            saved = json.loads(self.meta_path.read_text(encoding="utf-8")).get("embedding_model", "")
        except (OSError, ValueError, AttributeError) as exc:
            raise LibraryError(f"Metadados do acervo ilegíveis ({self.meta_path}): {exc}") from exc
        if saved and saved != self.embedding_model:
            raise LibraryError(
                f"O acervo foi indexado com o embedding `{saved}`, mas o .env pede "
                f"`{self.embedding_model}`. Volte o EMBEDDING_MODEL ou apague o índice e reindexe."
            )

    def load_docs(self) -> Any:
        if not self.docs_path.exists():
            return self._docs_factory()
        self._check_embedding_model()
        try:
            with self.docs_path.open("rb") as fh:
                return pickle.load(fh)  # noqa: S301 (arquivo local criado pelo próprio app)
        except (OSError, pickle.UnpicklingError, EOFError, AttributeError, ImportError) as exc:
            raise LibraryError(
                f"Índice do acervo ilegível ({self.docs_path}): {exc}. "
                "Se você atualizou o PaperQA2, apague o acervo pela barra lateral e reindexe."
            ) from exc

    def save_docs(self, docs: Any) -> None:
        try:
            _atomic_write_bytes(self.docs_path, pickle.dumps(docs))
            meta = {"embedding_model": self.embedding_model}
            _atomic_write_bytes(self.meta_path, json.dumps(meta).encode("utf-8"))
        except (OSError, pickle.PicklingError) as exc:
            raise LibraryError(f"Não foi possível salvar o índice: {exc}") from exc

    def reset(self) -> Any:
        """Apaga índice e manifesto (os arquivos em documentos/ ficam)."""
        for path in (self.docs_path, self.manifest_path, self.meta_path):
            path.unlink(missing_ok=True)
        return self._docs_factory()
