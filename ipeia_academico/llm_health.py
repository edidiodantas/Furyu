"""Diz se a IA configurada está pronta para uso, sem gastar chamadas pagas."""

from __future__ import annotations

from collections.abc import Mapping

from ipeia_academico.config import AppConfig, missing_api_key
from ipeia_academico.ollama_health import FetchJson, OllamaHealth, check_ollama, fetch_json


def check_llm(config: AppConfig, env: Mapping[str, str], *, fetch: FetchJson = fetch_json) -> OllamaHealth:
    """Ollama: consulta o servidor. Provedores remotos: só confere se há chave.

    Não fazemos uma chamada de teste aos provedores pagos para não gerar custo
    a cada abertura da tela; erros de chave aparecem na primeira pergunta.
    """
    if config.provider.name == "ollama":
        return check_ollama(config.llm_api_base, config.llm_model, fetch=fetch)

    missing = missing_api_key(config, env)
    if missing:
        return OllamaHealth(False, f"Falta a chave `{missing}` no .env para usar {config.provider.name}.")
    where = config.llm_api_base or config.provider.name
    return OllamaHealth(True, f"IA configurada: `{config.llm_name}` em {where} (chave não testada).")
