"""Referências e citações no padrão ABNT (funções puras, sem I/O).

Fontes das regras:
- Citação (NBR 10520:2023): autor em maiúsculas e minúsculas dentro dos
  parênteses, como em (Silva, 2020, p. 62); autores da mesma obra separados
  por ponto e vírgula; quatro ou mais autores podem virar "et al." em itálico.
  Conferido no guia da FZEA/USP sobre a NBR 10520:2023.
- Referência (NBR 6023:2018): sobrenome em maiúsculas, título da obra (livro)
  ou do periódico (artigo) em negrito, [S. l.] e [s. n.] quando faltam local
  e editora. Estas regras vêm de conhecimento geral da norma e NÃO foram
  conferidas no texto oficial; revise a lista final antes de entregar.

Algumas instituições ainda pedem o sobrenome em maiúsculas na citação
(regra da versão antiga). Por isso a caixa alta é opcional
(`uppercase=True`, ligada por CITATION_UPPERCASE no .env).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any

MAX_AUTHORS = 30
_YEAR_RE = re.compile(r"^(1[5-9]\d{2}|20\d{2})$")
_SUFFIXES = {"filho", "júnior", "junior", "jr.", "neto", "sobrinho"}
_MONTHS = ("jan.", "fev.", "mar.", "abr.", "maio", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez.")
ET_AL = "*et al.*"


class DocType(str, Enum):
    BOOK = "livro"
    ARTICLE = "artigo"
    ONLINE = "online"


class BibReferenceError(ValueError):
    """Dados insuficientes ou inválidos para montar a referência."""


@dataclass(frozen=True)
class BibReference:
    doc_type: DocType
    title: str
    year: str
    authors: tuple[str, ...] = field(default_factory=tuple)  # cada um "Sobrenome, Prenome"
    subtitle: str = ""
    edition: str = ""
    place: str = ""
    publisher: str = ""
    journal: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    accessed: str = ""  # data ISO (AAAA-MM-DD)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["doc_type"] = self.doc_type.value
        data["authors"] = list(self.authors)
        return data


# ---------------------------------------------------------------------------
# Entrada: nomes de autores e validação
# ---------------------------------------------------------------------------
def normalize_author(raw: str) -> str:
    """Devolve "Sobrenome, Prenome". Aceita também "Prenome Sobrenome".

    Sufixos como Filho e Júnior ficam junto do sobrenome (ex.: "Silva Filho").
    """
    name = " ".join((raw or "").split()).strip(" ;,")
    if not name:
        return ""
    if "," in name:
        surname, given = (part.strip() for part in name.split(",", 1))
        return f"{surname}, {given}" if given else surname
    parts = name.split(" ")
    if len(parts) == 1:
        return parts[0]
    cut = -2 if len(parts) > 2 and parts[-1].lower() in _SUFFIXES else -1
    return f"{' '.join(parts[cut:])}, {' '.join(parts[:cut])}"


def parse_authors(raw: str) -> tuple[str, ...]:
    """Um autor por linha ou separados por ponto e vírgula."""
    pieces = re.split(r"[;\n]", raw or "")
    authors = tuple(a for a in (normalize_author(p) for p in pieces) if a)
    if len(authors) > MAX_AUTHORS:
        raise BibReferenceError(f"Informe no máximo {MAX_AUTHORS} autores.")
    return authors


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def build_reference(data: dict[str, Any]) -> BibReference:
    """Valida dados vindos do formulário ou do manifesto."""
    try:
        doc_type = DocType(_clean(data.get("doc_type")) or DocType.BOOK.value)
    except ValueError as exc:
        raise BibReferenceError(f"Tipo de documento inválido: {data.get('doc_type')!r}.") from exc
    title = _clean(data.get("title"))
    if not title:
        raise BibReferenceError("Informe o título.")
    year = _clean(data.get("year"))
    if not _YEAR_RE.match(year):
        raise BibReferenceError("Informe o ano com 4 dígitos (ex.: 2020).")
    authors_raw = data.get("authors") or ()
    authors = (
        parse_authors(authors_raw)
        if isinstance(authors_raw, str)
        else tuple(a for a in (normalize_author(x) for x in authors_raw) if a)
    )
    if doc_type is DocType.ARTICLE and not _clean(data.get("journal")):
        raise BibReferenceError("Para artigo, informe o nome do periódico.")
    accessed = _clean(data.get("accessed"))
    if accessed:
        try:
            date.fromisoformat(accessed)
        except ValueError as exc:
            raise BibReferenceError("Data de acesso inválida (use AAAA-MM-DD).") from exc
    url = _clean(data.get("url"))
    if url and not url.startswith(("http://", "https://")):
        raise BibReferenceError("O endereço (URL) deve começar com http:// ou https://.")
    return BibReference(
        doc_type=doc_type,
        title=title,
        year=year,
        authors=authors,
        subtitle=_clean(data.get("subtitle")),
        edition=_clean(data.get("edition")),
        place=_clean(data.get("place")),
        publisher=_clean(data.get("publisher")),
        journal=_clean(data.get("journal")),
        volume=_clean(data.get("volume")),
        number=_clean(data.get("number")),
        pages=_clean(data.get("pages")),
        doi=_clean(data.get("doi")).removeprefix("https://doi.org/"),
        url=url,
        accessed=accessed,
    )


# ---------------------------------------------------------------------------
# Saída: referência (lista final) e citação no texto
# ---------------------------------------------------------------------------
def _surname(author: str) -> str:
    return author.split(",", 1)[0].strip()


def _reference_author(author: str) -> str:
    surname, _, given = author.partition(",")
    surname = surname.strip().upper()
    return f"{surname}, {given.strip()}" if given.strip() else surname


def _title_entry(title: str) -> str:
    """Sem autor, a entrada é pelo título com a primeira palavra em maiúsculas."""
    first, _, rest = title.partition(" ")
    return f"{first.upper()} {rest}".strip()


def _edition(edition: str) -> str:
    digits = re.sub(r"\D", "", edition)
    if not edition or digits == "1":
        return ""
    return f"{digits}. ed." if digits else edition


def _access_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def _online_tail(ref: BibReference) -> str:
    parts = []
    if ref.doi:
        parts.append(f"DOI: {ref.doi}.")
    if ref.url:
        parts.append(f"Disponível em: {ref.url}.")
        if ref.accessed:
            parts.append(f"Acesso em: {_access_date(ref.accessed)}.")
    return " ".join(parts)


def format_reference(ref: BibReference) -> str:
    """Referência em Markdown (negrito com **)."""
    full_title = f"{ref.title}: {ref.subtitle}" if ref.subtitle else ref.title
    if ref.authors:
        head = "; ".join(_reference_author(a) for a in ref.authors) + "."
        title_md = f"**{ref.title}**" + (f": {ref.subtitle}" if ref.subtitle else "")
    else:
        head = ""
        full_title = _title_entry(full_title)
        title_md = full_title  # sem autor, o destaque já é a primeira palavra

    if ref.doc_type is DocType.ARTICLE:
        details = [f"**{ref.journal}**"]
        if ref.place:
            details.append(ref.place)
        details += [f"v. {ref.volume}"] if ref.volume else []
        details += [f"n. {ref.number}"] if ref.number else []
        details += [f"p. {ref.pages}"] if ref.pages else []
        details.append(ref.year)
        body = f"{full_title}. {', '.join(details)}."
    elif ref.doc_type is DocType.BOOK:
        edition = _edition(ref.edition)
        imprint = f"{ref.place or '[S. l.]'}: {ref.publisher or '[s. n.]'}, {ref.year}."
        body = f"{title_md}. " + (f"{edition} " if edition else "") + imprint
    else:
        body = f"{title_md}. {ref.year}."

    text = " ".join(x for x in (head, body, _online_tail(ref)) if x)
    return re.sub(r"\.\.+", ".", text)


def citation_author_label(ref: BibReference, *, uppercase: bool = False) -> str:
    """Autoria como aparece na citação: Silva / Silva; Souza / Silva *et al.*"""
    if not ref.authors:
        label = ref.title.split(" ", 1)[0]
        return label.upper() if uppercase else label
    names = [_surname(a) for a in ref.authors]
    names = [n.upper() if uppercase else n for n in names]
    if len(names) >= 4:
        return f"{names[0]} {ET_AL}"
    return "; ".join(names)


def page_locator(pages: str) -> str:
    """"3" → "p. 3"; "3-4" → "p. 3-4"; vazio → ""."""
    pages = (pages or "").strip()
    return f"p. {pages}" if pages else ""


def format_citation_inner(ref: BibReference, pages: str = "", *, uppercase: bool = False) -> str:
    """Conteúdo de uma citação sem os parênteses: "Silva, 2020, p. 3"."""
    parts = [citation_author_label(ref, uppercase=uppercase), ref.year]
    locator = page_locator(pages)
    if locator:
        parts.append(locator)
    return ", ".join(parts)


def reference_sort_key(text: str) -> str:
    """A lista de referências é em ordem alfabética, ignorando o Markdown."""
    return re.sub(r"[*_]", "", text).casefold()


def prefill_from_catalog(
    *,
    title: str,
    year: int | str | None,
    authors: str,
    venue: str,
    doi: str,
    url: str,
    names_are_given_first: bool,
    today: date,
) -> dict[str, Any]:
    """Dados iniciais da referência a partir de um resultado de busca.

    Só aproveita os autores quando o catálogo os entrega como "Prenome
    Sobrenome" separados por vírgula (Semantic Scholar e Crossref). No
    Oasisbr o nome já vem com vírgula ("Silva, João"), e a lista separada por
    vírgulas fica ambígua; nesse caso os autores ficam para você preencher.
    """
    author_list = (
        [normalize_author(a) for a in authors.split(",")] if names_are_given_first and authors else []
    )
    return {
        "doc_type": (DocType.ARTICLE if venue else DocType.ONLINE).value,
        "title": title,
        "year": str(year or ""),
        "authors": [a for a in author_list if a],
        "journal": venue,
        "doi": doi,
        "url": "" if doi else url,
        "accessed": "" if doi or not url else today.isoformat(),
    }
