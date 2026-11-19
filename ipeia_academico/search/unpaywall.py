"""Unpaywall: acha o PDF legal em acesso aberto a partir do DOI."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from ipeia_academico.search.http import USER_AGENT, UnpaywallEmailError, http_client
from ipeia_academico.search.models import PaperHit
from ipeia_academico.search.parsing import pdf_from_unpaywall

UNPAYWALL = "https://api.unpaywall.org/v2/{doi}"


def unpaywall_pdf_url(doi: str, email: str, *, client: httpx.Client | None = None) -> str:
    doi = doi.strip()
    email = email.strip()
    if not doi or "@" not in email:
        return ""
    url = UNPAYWALL.format(doi=quote(doi, safe="/"))
    with http_client(client, 30.0) as http:
        r = http.get(url, params={"email": email}, headers={"User-Agent": USER_AGENT})
        if r.status_code == 404:
            return ""
        if r.status_code == 422:
            raise UnpaywallEmailError(
                "Unpaywall recusou o e-mail. Use um e-mail real em CONTACT_EMAIL no .env."
            )
        r.raise_for_status()
        data = r.json()
    return pdf_from_unpaywall(data)


def attach_unpaywall_pdfs(
    hits: list[PaperHit], email: str, *, client: httpx.Client | None = None
) -> str:
    """Preenche pdf_url via Unpaywall quando o catálogo não trouxe PDF.

    Nunca derruba a busca: devolve um aviso (string vazia se tudo bem).
    Antes, um e-mail recusado (422) cancelava a busca inteira, mesmo com
    resultados já encontrados.
    """
    if "@" not in (email or ""):
        return ""
    missing = [h for h in hits if not h.pdf_url and h.doi]
    if not missing:
        return ""
    with http_client(client, 30.0) as http:
        for hit in missing:
            try:
                url = unpaywall_pdf_url(hit.doi, email, client=http)
            except UnpaywallEmailError as exc:
                return str(exc)
            except (httpx.HTTPError, ValueError):
                continue  # um DOI com problema não deve parar os demais
            if url:
                hit.pdf_url = url
                hit.source = f"{hit.source}+unpaywall"
    return ""
