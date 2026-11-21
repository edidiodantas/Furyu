"""Infraestrutura HTTP compartilhada pelos catálogos."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import httpx

USER_AGENT = (
    "ipeia-academico/0.2 (uso academico individual; "
    "+https://github.com/edidiodantas/Furyu)"
)
MAX_PDF_BYTES = 40 * 1024 * 1024
MAX_RESULTS = 20


class SearchError(RuntimeError):
    """Nenhum catálogo respondeu."""


class UnpaywallEmailError(RuntimeError):
    """Unpaywall rejeitou o CONTACT_EMAIL (HTTP 422)."""


@contextmanager
def http_client(client: httpx.Client | None, timeout: float) -> Iterator[httpx.Client]:
    """Usa o cliente injetado (testes) ou cria um temporário."""
    if client is not None:
        yield client
        return
    with httpx.Client(timeout=timeout, follow_redirects=True) as own:
        yield own


def default_headers(s2_key: str = "") -> dict[str, str]:
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if s2_key:
        h["x-api-key"] = s2_key
    return h
