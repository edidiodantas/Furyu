"""Funções puras de extração de metadados das respostas dos catálogos."""

from __future__ import annotations

import re

from ipeia_academico.search.models import PaperHit

SCIELO_PDF = "https://www.scielo.br/scielo.php?script=sci_pdf&pid={pid}&lng=pt&tlng=pt"
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.I)
# PID SciELO: S + ISSN (o último dígito do ISSN pode ser X) + ano + 9 dígitos.
_PID_RE = re.compile(r"(S\d{4}-\d{3}[\dX]\d{13})", re.I)


def s2_authors(raw: list | None) -> str:
    names = []
    for item in raw or []:
        name = (item or {}).get("name") or ""
        if name:
            names.append(name)
    return ", ".join(names[:8])


def crossref_authors(raw: list | None) -> str:
    names = []
    for item in raw or []:
        given = (item or {}).get("given") or ""
        family = (item or {}).get("family") or ""
        name = f"{given} {family}".strip() or (item or {}).get("name") or ""
        if name:
            names.append(name)
    return ", ".join(names[:8])


def crossref_year(item: dict) -> int | None:
    for key in ("published-print", "published-online", "published"):
        parts = ((item.get(key) or {}).get("date-parts") or [[]])
        if parts and parts[0] and parts[0][0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                continue
    return None


def looks_like_pdf_url(url: str) -> bool:
    u = url.lower()
    if not u.startswith("http"):
        return False
    if u.startswith("https://doi.org/") or u.startswith("http://doi.org/"):
        return False
    if (
        u.endswith(".pdf")
        or "/pdf" in u
        or "pdf=" in u
        or "format=pdf" in u
        or "type=printable" in u
        or "script=sci_pdf" in u
    ):
        return True
    return False


def pdf_from_unpaywall(data: dict) -> str:
    locations = []
    best = data.get("best_oa_location")
    if best:
        locations.append(best)
    for loc in data.get("oa_locations") or []:
        if loc and loc not in locations:
            locations.append(loc)
    for loc in locations:
        pdf = (loc.get("url_for_pdf") or "").strip()
        if pdf:
            return pdf
        url = (loc.get("url") or "").strip()
        if looks_like_pdf_url(url):
            return url
    return ""


def vufind_authors(authors: dict | None) -> str:
    names = []
    block = authors or {}
    for role in ("primary", "secondary", "corporate"):
        group = block.get(role) or {}
        if isinstance(group, dict):
            names.extend(group.keys())
    cleaned = []
    for name in names:
        n = re.sub(r"\s*\[[^\]]*\]", "", str(name)).strip()
        if n:
            cleaned.append(n)
    return ", ".join(cleaned[:8])


def first_doi(*texts: str) -> str:
    for text in texts:
        m = _DOI_RE.search(text or "")
        if m:
            return m.group(0).rstrip(").,;")
    return ""


def scielo_pid(*texts: str) -> str:
    for text in texts:
        m = _PID_RE.search(text or "")
        if m:
            return m.group(1).upper()
    return ""


def year_from_pid(pid: str) -> int | None:
    if len(pid) >= 14 and pid[0] == "S":
        try:
            y = int(pid[10:14])
        except ValueError:
            return None
        if 1900 <= y <= 2100:
            return y
    return None


def scielo_pdf_url(pid: str) -> str:
    pid = (pid or "").strip()
    if not pid:
        return ""
    return SCIELO_PDF.format(pid=pid)


def crossref_title(item: dict) -> str:
    for key in ("title", "short-title", "subtitle"):
        for raw in item.get(key) or []:
            t = (raw or "").strip()
            if t and not t.lower().startswith("http"):
                return t
    return "Sem título"


def dedupe(hits: list[PaperHit]) -> list[PaperHit]:
    seen: set[str] = set()
    out: list[PaperHit] = []
    for hit in hits:
        key = (hit.doi or hit.paper_id).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return out
