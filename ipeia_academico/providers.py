"""Catálogo de provedores de LLM suportados (via LiteLLM, usado pelo PaperQA2).

Para trocar de IA basta mudar LLM_PROVIDER e LLM_MODEL no .env. A chave de
API é lida da variável de ambiente padrão de cada provedor (nunca do código).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    name: str
    litellm_prefix: str
    api_key_env: str  # vazio = não precisa de chave
    is_local: bool
    requires_api_base: bool = False
    default_api_base: str = ""
    sends_temperature: bool = True


# Prefixos conforme a convenção do LiteLLM ("<provedor>/<modelo>").
PROVIDERS: dict[str, Provider] = {
    "ollama": Provider(
        "ollama", "ollama/", "", is_local=True, default_api_base="http://localhost:11434"
    ),
    # Servidor local compatível com a API da OpenAI (LM Studio, vLLM, llama.cpp server).
    "openai_compatible": Provider(
        "openai_compatible", "openai/", "OPENAI_API_KEY", is_local=True, requires_api_base=True
    ),
    "openai": Provider("openai", "openai/", "OPENAI_API_KEY", is_local=False),
    # Modelos Claude atuais recusam temperature (HTTP 400): não enviamos.
    "anthropic": Provider(
        "anthropic", "anthropic/", "ANTHROPIC_API_KEY", is_local=False, sends_temperature=False
    ),
    "gemini": Provider("gemini", "gemini/", "GEMINI_API_KEY", is_local=False),
    "openrouter": Provider("openrouter", "openrouter/", "OPENROUTER_API_KEY", is_local=False),
}


class UnknownProviderError(ValueError):
    pass


def get_provider(name: str) -> Provider:
    key = (name or "").strip().lower()
    try:
        return PROVIDERS[key]
    except KeyError as exc:
        valid = ", ".join(sorted(PROVIDERS))
        raise UnknownProviderError(f"LLM_PROVIDER inválido: {name!r}. Use um de: {valid}.") from exc


def litellm_model_name(provider: Provider, model: str) -> str:
    """Adiciona o prefixo do provedor se o usuário não o escreveu."""
    model = model.strip()
    return model if model.startswith(provider.litellm_prefix) else f"{provider.litellm_prefix}{model}"
