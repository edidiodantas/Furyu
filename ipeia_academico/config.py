"""Configuração do IPeia Acadêmico lida do ambiente.

A função `load_config` é pura: recebe um Mapping (normalmente `os.environ`)
e devolve um `AppConfig` imutável. Assim os testes não dependem do .env real.

Compatibilidade: com LLM_PROVIDER=ollama (padrão), OLLAMA_MODEL e
OLLAMA_BASE_URL continuam valendo se LLM_MODEL / LLM_API_BASE não forem dados.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from ipeia_academico.providers import Provider, UnknownProviderError, get_provider, litellm_model_name

DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_MODEL = "qwen3.5:4b"
DEFAULT_EMBEDDING_MODEL = "st-multi-qa-MiniLM-L6-cos-v1"
DEFAULT_ANSWER_LANGUAGE = "português do Brasil"
DEFAULT_ANSWER_LENGTH = "cerca de 300 palavras"
DEFAULT_EVIDENCE_K = 10
DEFAULT_ANSWER_MAX_SOURCES = 5
DEFAULT_OLLAMA_TEMPERATURE = 0.0

# Validação simples: só evita placeholders óbvios e valores sem domínio.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PLACEHOLDER_DOMAINS = ("exemplo.com", "example.com", "suaescola.edu.br", "escola.edu.br")


class ConfigError(ValueError):
    """Valor inválido no .env."""


@dataclass(frozen=True)
class AppConfig:
    provider: Provider
    llm_model: str
    llm_api_base: str
    summary_llm_model: str
    llm_temperature: float | None
    embedding_model: str
    embedding_api_base: str
    pdf_dir: Path
    pqa_home: Path
    contact_email: str
    semantic_scholar_key: str
    answer_language: str
    answer_length: str
    evidence_k: int
    answer_max_sources: int

    @property
    def llm_name(self) -> str:
        """Nome no formato do LiteLLM (ex.: `ollama/llama3.2:3b`, `anthropic/claude-opus-5-5`)."""
        return litellm_model_name(self.provider, self.llm_model)

    @property
    def summary_llm_name(self) -> str:
        return litellm_model_name(self.provider, self.summary_llm_model)

    @property
    def is_local(self) -> bool:
        """True se nada sai do computador (LLM local e embedding local)."""
        return self.provider.is_local and not self.embedding_is_remote

    @property
    def embedding_is_remote(self) -> bool:
        local_prefixes = ("st-", "ollama/", "sparse", "hybrid-st-")
        return not self.embedding_model.startswith(local_prefixes)

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


def _get(env: Mapping[str, str], key: str, default: str = "") -> str:
    return (env.get(key) or "").strip() or default


def _resolve_path(raw: str, root: Path) -> Path:
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (root / path)


def _validate_url(name: str, url: str) -> str:
    url = url.strip().rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        raise ConfigError(f"{name} deve começar com http:// ou https:// (recebido: {url!r}).")
    return url


def _validate_model(name: str, model: str) -> str:
    if not model:
        raise ConfigError(f"{name} está vazio.")
    if any(ch.isspace() for ch in model):
        raise ConfigError(f"{name} não pode ter espaços (recebido: {model!r}).")
    return model


def _positive_int(env: Mapping[str, str], key: str, default: int, maximum: int) -> int:
    raw = _get(env, key)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} deve ser um número inteiro (recebido: {raw!r}).") from exc
    if not 1 <= value <= maximum:
        raise ConfigError(f"{key} deve estar entre 1 e {maximum} (recebido: {value}).")
    return value


def _temperature(env: Mapping[str, str], provider: Provider) -> float | None:
    """None = não enviar temperature (alguns modelos recusam o parâmetro)."""
    raw = _get(env, "LLM_TEMPERATURE")
    if not raw:
        return DEFAULT_OLLAMA_TEMPERATURE if provider.name == "ollama" else None
    if not provider.sends_temperature:
        raise ConfigError(
            f"O provedor {provider.name} não aceita LLM_TEMPERATURE com os modelos atuais; "
            "deixe a variável vazia."
        )
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"LLM_TEMPERATURE deve ser um número (recebido: {raw!r}).") from exc
    if not 0.0 <= value <= 2.0:
        raise ConfigError(f"LLM_TEMPERATURE deve estar entre 0 e 2 (recebido: {value}).")
    return value


def load_config(env: Mapping[str, str], root: Path) -> AppConfig:
    """Monta o AppConfig a partir de um Mapping de variáveis de ambiente.

    `root` é a pasta do projeto, usada para resolver caminhos relativos.
    Levanta ConfigError se algum valor for inválido.
    """
    try:
        provider = get_provider(_get(env, "LLM_PROVIDER", DEFAULT_PROVIDER))
    except UnknownProviderError as exc:
        raise ConfigError(str(exc)) from exc

    is_ollama = provider.name == "ollama"
    model = _get(env, "LLM_MODEL") or (_get(env, "OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL) if is_ollama else "")
    model = _validate_model("LLM_MODEL", model)

    api_base = _get(env, "LLM_API_BASE") or (_get(env, "OLLAMA_BASE_URL") if is_ollama else "")
    api_base = _validate_url("LLM_API_BASE", api_base or provider.default_api_base)
    if provider.requires_api_base and not api_base:
        raise ConfigError(f"O provedor {provider.name} exige LLM_API_BASE (ex.: http://localhost:1234/v1).")

    summary_model = _validate_model("SUMMARY_LLM_MODEL", _get(env, "SUMMARY_LLM_MODEL", model))
    email = _get(env, "CONTACT_EMAIL")

    return AppConfig(
        provider=provider,
        llm_model=model,
        llm_api_base=api_base,
        summary_llm_model=summary_model,
        llm_temperature=_temperature(env, provider),
        embedding_model=_validate_model(
            "EMBEDDING_MODEL", _get(env, "EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        ),
        embedding_api_base=_validate_url("EMBEDDING_API_BASE", _get(env, "EMBEDDING_API_BASE")),
        pdf_dir=_resolve_path(_get(env, "PDF_DIR", "./documentos"), root),
        pqa_home=_resolve_path(_get(env, "PQA_HOME", "./.pqa"), root),
        # E-mail placeholder é tratado como ausente: evita o erro 422 do Unpaywall.
        contact_email=email if is_valid_contact_email(email) else "",
        semantic_scholar_key=_get(env, "SEMANTIC_SCHOLAR_API_KEY"),
        answer_language=_get(env, "ANSWER_LANGUAGE", DEFAULT_ANSWER_LANGUAGE),
        answer_length=_get(env, "ANSWER_LENGTH", DEFAULT_ANSWER_LENGTH),
        evidence_k=_positive_int(env, "EVIDENCE_K", DEFAULT_EVIDENCE_K, 100),
        answer_max_sources=_positive_int(env, "ANSWER_MAX_SOURCES", DEFAULT_ANSWER_MAX_SOURCES, 50),
    )


def missing_api_key(config: AppConfig, env: Mapping[str, str]) -> str:
    """Nome da variável de chave que falta, ou "" se não falta nada."""
    key_env = config.provider.api_key_env
    if not key_env or config.provider.name == "openai_compatible":
        return ""  # servidores locais compatíveis geralmente não exigem chave
    return "" if _get(env, key_env) else key_env
