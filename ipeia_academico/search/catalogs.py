"""Catálogos de busca: Oasisbr (IBICT), Semantic Scholar e Crossref."""

from __future__ import annotations

import re
import time

import httpx

from ipeia_academico.search.http import MAX_RESULTS, default_headers, http_client
from ipeia_academico.search.models import PaperHit
from ipeia_academico.search.parsing import (
    crossref_authors,
    crossref_title,
    crossref_year,
    first_doi,
    looks_like_pdf_url,
    s2_authors,
    scielo_pid,
    vufind_authors,
    year_from_pid,
)

S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_SEARCH = "https://api.crossref.org/works"
OASISBR_SEARCH = "https://oasisbr.ibict.br/vufind/api/v1/search"


def search_oasisbr(
    query: str, *, limit: int = 8, client: httpx.Client | None = None
) -> list[PaperHit]:
    """Busca no Oasisbr (IBICT) — API VuFind pública, sem chave."""
    q = query.strip()
    if not q:
        return []
    params: list[tuple[str, str | int]] = [
        ("lookfor", q),
        ("type", "AllFields"),
        ("limit", max(1, min(limit, MAX_RESULTS))),
        ("filter[]", "format:article"),
    ]
    with http_client(client, 35.0) as http:
        r = http.get(OASISBR_SEARCH, params=params, headers=default_headers())
        r.raise_for_status()
        records = list(r.json().get("records") or [])
        if not records:
            # Sem filtro de formato: inclui teses, dissertações e livros.
            params = [("lookfor", q), ("type", "AllFields"), ("limit", max(1, min(limit, MAX_RESULTS)))]
            r = http.get(OASISBR_SEARCH, params=params, headers=default_headers())
            r.raise_for_status()
            records = list(r.json().get("records") or [])

    hits: list[PaperHit] = []
    for item in records:
        urls = [(u or {}).get("url") or "" for u in (item.get("urls") or [])]
        blob = " ".join(
            [
                str(item.get("id") or ""),
                str(item.get("oai_identifier_st") or ""),
                *urls,
            ]
        )
        doi = first_doi(*urls, blob)
        pid = scielo_pid(blob, doi)
        if pid and not doi:
            doi = f"10.1590/{pid}"
        pdf_url = ""
        for u in urls:
            if looks_like_pdf_url(u):
                pdf_url = u
                break
        source = "scielo" if pid else "oasisbr"
        venue = "SciELO" if pid else "Oasisbr"
        hits.append(
            PaperHit(
                paper_id=str(item.get("id") or doi or item.get("title") or ""),
                title=(item.get("title") or "Sem título").strip(),
                year=year_from_pid(pid),
                authors=vufind_authors(item.get("authors")),
                venue=venue,
                doi=doi,
                abstract="",
                pdf_url=pdf_url,
                source=source,
            )
        )
    return hits


def search_semantic_scholar(
    query: str,
    *,
    api_key: str = "",
    limit: int = 8,
    open_pdf_only: bool = False,
    client: httpx.Client | None = None,
    sleep=time.sleep,
) -> list[PaperHit]:
    q = query.strip()
    if not q:
        return []
    params: list[tuple[str, str | int]] = [
        ("query", q),
        ("limit", max(1, min(limit, MAX_RESULTS))),
        (
            "fields",
            "title,year,authors,abstract,externalIds,openAccessPdf,venue,isOpenAccess",
        ),
    ]
    if open_pdf_only:
        params.append(("openAccessPdf", ""))

    payload: dict = {}
    with http_client(client, 30.0) as http:
        for attempt in range(2):
            r = http.get(S2_SEARCH, params=params, headers=default_headers(api_key))
            if r.status_code == 429:
                if attempt == 0:
                    sleep(1.5)
                    continue
                raise RuntimeError(
                    "Semantic Scholar pediu para esperar (limite de buscas). "
                    "Aguarde 1 minuto ou coloque SEMANTIC_SCHOLAR_API_KEY no .env (chave grátis)."
                )
            r.raise_for_status()
            payload = r.json()
            break

    hits: list[PaperHit] = []
    for item in payload.get("data") or []:
        ext = item.get("externalIds") or {}
        doi = (ext.get("DOI") or "").strip()
        oa = item.get("openAccessPdf") or {}
        pdf_url = (oa.get("url") or "").strip()
        hits.append(
            PaperHit(
                paper_id=str(item.get("paperId") or doi or item.get("title") or ""),
                title=(item.get("title") or "Sem título").strip(),
                year=item.get("year"),
                authors=s2_authors(item.get("authors")),
                venue=(item.get("venue") or "").strip(),
                doi=doi,
                abstract=((item.get("abstract") or "")[:500]).strip(),
                pdf_url=pdf_url,
                source="semantic-scholar",
            )
        )
    return hits


def search_crossref(
    query: str, *, email: str = "", limit: int = 8, client: httpx.Client | None = None
) -> list[PaperHit]:
    q = query.strip()
    if not q:
        return []
    params: dict[str, str | int] = {
        "query": q,
        "rows": max(1, min(limit, MAX_RESULTS)),
        "filter": "type:journal-article",
        "select": "DOI,title,author,published-print,published-online,published,container-title,abstract,link",
    }
    if email and "@" in email:
        params["mailto"] = email

    with http_client(client, 30.0) as http:
        r = http.get(CROSSREF_SEARCH, params=params, headers=default_headers())
        r.raise_for_status()
        payload = r.json()

    hits: list[PaperHit] = []
    for item in (payload.get("message") or {}).get("items") or []:
        doi = (item.get("DOI") or "").strip()
        title = crossref_title(item)
        venues = item.get("container-title") or []
        venue = (venues[0] if venues else "").strip()
        abstract = re.sub(r"<[^>]+>", "", item.get("abstract") or "")
        pdf_url = ""
        for link in item.get("link") or []:
            if (link.get("content-type") or "") == "application/pdf":
                candidate = (link.get("URL") or "").strip()
                if looks_like_pdf_url(candidate):
                    pdf_url = candidate
                    break
        hits.append(
            PaperHit(
                paper_id=doi or title,
                title=title,
                year=crossref_year(item),
                authors=crossref_authors(item.get("author")),
                venue=venue,
                doi=doi,
                abstract=abstract[:500].strip(),
                pdf_url=pdf_url,
                source="crossref",
            )
        )
    return hits
