"""Busca acadêmica pública (sem login).

Oasisbr (IBICT): busca brasileira (artigos, teses, repositórios) — API VuFind grátis.
Semantic Scholar / Crossref: fallback internacional.
Unpaywall: tenta o PDF legal em acesso aberto (precisa de e-mail de contato).
SciELO: PDF pelo PID quando o Oasisbr aponta para a coleção.
Não baixa artigo fechado (paywall).

Todas as funções de rede aceitam `client` (httpx.Client) injetado, para teste.
"""

from ipeia_academico.search.download import download_pdf, safe_pdf_filename
from ipeia_academico.search.http import SearchError, UnpaywallEmailError
from ipeia_academico.search.models import PaperHit
from ipeia_academico.search.service import resolve_pdf_url, search_academic

__all__ = [
    "PaperHit",
    "SearchError",
    "UnpaywallEmailError",
    "download_pdf",
    "resolve_pdf_url",
    "safe_pdf_filename",
    "search_academic",
]
