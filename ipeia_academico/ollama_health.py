"""Checagem do servidor Ollama (está no ar? o modelo está instalado?)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

FetchJson = Callable[[str, float], dict[str, Any]]


@dataclass(frozen=True)
class OllamaHealth:
    ok: bool
    message: str


def fetch_json(url: str, timeout: float) -> dict[str, Any]:
    """GET simples que devolve o JSON (implementação padrão, injetável nos testes)."""
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (URL vem do .env)
        return json.loads(resp.read().decode("utf-8") or "{}")


def model_is_installed(model: str, installed: list[str]) -> bool:
    """`qwen3.5` casa com `qwen3.5:latest`; `qwen3.5:4b` precisa casar exato."""
    for name in installed:
        if name == model or (":" not in model and name.startswith(f"{model}:")):
            return True
    return False


def check_ollama(
    base_url: str,
    model: str,
    *,
    fetch: FetchJson = fetch_json,
    timeout: float = 3.0,
) -> OllamaHealth:
    try:
        payload = fetch(f"{base_url}/api/tags", timeout)
    except urllib.error.URLError as exc:
        return OllamaHealth(False, f"Ollama inacessível em {base_url} ({exc.reason}).")
    except (OSError, ValueError) as exc:
        return OllamaHealth(False, f"Falha ao consultar o Ollama: {exc}")

    installed = [
        (item.get("name") or item.get("model") or "")
        for item in (payload.get("models") or [])
        if isinstance(item, dict)
    ]
    installed = [n for n in installed if n]

    if model_is_installed(model, installed):
        return OllamaHealth(True, f"Ollama ok · modelo `{model}` encontrado.")
    if installed:
        preview = ", ".join(installed[:8])
        return OllamaHealth(
            False,
            f"Ollama ok, mas `{model}` não está instalado. "
            f"Rode `ollama pull {model}`. Disponíveis: {preview}",
        )
    return OllamaHealth(False, "Ollama respondeu, mas nenhum modelo está instalado.")
