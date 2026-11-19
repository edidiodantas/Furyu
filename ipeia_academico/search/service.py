"""Orquestra a busca: catálogos em cascata + Unpaywall + deduplicação."""

from __future__ import annotations

import httpx

from ipeia_academico.search.catalogs import search_crossref, search_oasisbr, search_semantic_scholar
from ipeia_academico.search.http import SearchError
from ipeia_academico.search.models import PaperHit
from ipeia_academico.search.parsing import dedupe, looks_like_pdf_url, scielo_pdf_url, scielo_pid
from ipeia_academico.search.unpaywall import attach_unpaywall_pdfs, unpaywall_pdf_url


def search_academic(
    query: str,
    *,
    s2_key: str = "",
    email: str = "",
    limit: int = 8,
    client: httpx.Client | None = None,
) -> tuple[list[PaperHit], str]:
    """Oasisbr primeiro; Semantic Scholar e Crossref se não houver resultado.

    Retorna (hits, nota_para_a_tela). Só levanta SearchError se todos os
    catálogos falharem por erro (e não por simplesmente não acharem nada).
    """
    q = (query or "").strip()
    if not q:
        return [], ""

    errors: list[str] = []
    hits: list[PaperHit] = []
    note = ""
    sources = (
        ("Oasisbr (IBICT)", lambda: search_oasisbr(q, limit=limit, client=client)),
        ("Semantic Scholar", lambda: search_semantic_scholar(q, api_key=s2_key, limit=limit, client=client)),
        ("Crossref", lambda: search_crossref(q, email=email, limit=limit, client=client)),
    )
    for name, run in sources:
        try:
            hits = run()
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            errors.append(f"{name} indisponível ({exc})")
            continue
        if hits:
            note = name
            break

    if not hits and len(errors) == len(sources):
        raise SearchError("Nenhum catálogo respondeu: " + "; ".join(errors))

    warning = attach_unpaywall_pdfs(hits, email, client=client)
    extras = [*errors, warning] if warning else errors
    if extras:
        note = f"{note} · avisos: {'; '.join(extras)}" if note else "; ".join(extras)
    return dedupe(hits), note


def resolve_pdf_url(
    hit: PaperHit, contact_email: str, *, client: httpx.Client | None = None
) -> str:
    if hit.pdf_url and looks_like_pdf_url(hit.pdf_url):
        return hit.pdf_url
    if hit.doi:
        url = unpaywall_pdf_url(hit.doi, contact_email, client=client)
        if url:
            return url
    pid = scielo_pid(hit.doi or "", hit.paper_id)
    if pid:
        return scielo_pdf_url(pid)
    return hit.pdf_url or ""
