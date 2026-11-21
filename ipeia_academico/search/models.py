"""Modelo de resultado de busca."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PaperHit:
    paper_id: str
    title: str
    year: int | None
    authors: str
    venue: str
    doi: str
    abstract: str
    pdf_url: str
    source: str  # oasisbr | scielo | semantic-scholar | crossref (+unpaywall)

    @property
    def has_open_pdf(self) -> bool:
        return bool(self.pdf_url)
