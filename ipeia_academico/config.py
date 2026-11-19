"""Configuração do IPeia Acadêmico lida do ambiente.

A função `load_config` é pura: recebe um Mapping (normalmente `os.environ`)
e devolve um `AppConfig` imutável. Assim os testes não dependem do .env real.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OLLAMA_MODEL = "qwen3.5:4b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_EMBEDDING_MODEL = "st-multi-qa-MiniLM-L6-cos-v1"
DEFAULT_ANSWER_LANGUAGE = "português do Brasil"

# Validação simples: só evita placeholders óbvios e valores sem domínio.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PLACEHOLDER_DOMAINS = ("exemplo.com", "example.com", "suaescola.edu.br", "escola.edu.br")


class ConfigError(ValueError):
    """Valor inválido no .env."""


@dataclass(frozen=True)
class AppConfig:
    ollama_model: str
    ollama_base_url: str
    embedding_model: str
    pdf_dir: Path
    pqa_home: Path
    contact_email: str
    semantic_scholar_key: str
    answer_language: str

    @property
    def llm_name(self) -> str:
        """Nome no formato do LiteLLM (prefixo `ollama/`)."""
        return f"ollama/{self.ollama_model}"

    @property
    def library_dir(self) -> Path:
        """Onde o acervo persistente (Docs + manifesto) é gravado."""
        return self.pqa_home / "acervo"


def is_valid_contact_email(email: str) -> bool:
    """E-mail plausível e que não seja o placeholder dos exemplos."""
    email = (email or "").strip()
    if not _EMAIL_RE.match(email):
        return False
    domain = email.rsplit("@", 1)[1].lower()
    return domain not in _PLACEHOLDER_DOMAINS


def _resolve_path(raw: str, root: Path) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (root / path)


def _validate_base_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ConfigError(
            f"OLLAMA_BASE_URL deve começar com http:// ou https:// (recebido: {url!r})."
        )
    return url


def _non_empty(env: Mapping[str, str], key: str, default: str) -> str:
    value = (env.get(key) or "").strip()
    return value or default


def load_config(env: Mapping[str, str], root: Path) -> AppConfig:
    """Monta o AppConfig a partir de um Mapping de variáveis de ambiente.

    `root` é a pasta do projeto, usada para resolver caminhos relativos.
    Levanta ConfigError se algum valor for inválido.
    """
    model = _non_empty(env, "OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    if any(ch.isspace() for ch in model):
        raise ConfigError(f"OLLAMA_MODEL não pode ter espaços (recebido: {model!r}).")

    email = (env.get("CONTACT_EMAIL") or "").strip()

    return AppConfig(
        ollama_model=model,
        ollama_base_url=_validate_base_url(
            _non_empty(env, "OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        ),
        embedding_model=_non_empty(env, "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        pdf_dir=_resolve_path(_non_empty(env, "PDF_DIR", "./documentos"), root),
        pqa_home=_resolve_path(_non_empty(env, "PQA_HOME", "./.pqa"), root),
        # E-mail placeholder é tratado como ausente: evita o erro 422 do Unpaywall.
        contact_email=email if is_valid_contact_email(email) else "",
        semantic_scholar_key=(env.get("SEMANTIC_SCHOLAR_API_KEY") or "").strip(),
        answer_language=_non_empty(env, "ANSWER_LANGUAGE", DEFAULT_ANSWER_LANGUAGE),
    )
