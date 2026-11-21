"""Download seguro de PDF em acesso aberto."""

from __future__ import annotations

import re
from pathlib import Path

import httpx

from ipeia_academico.library import sanitize_filename, unique_path
from ipeia_academico.search.http import MAX_PDF_BYTES, USER_AGENT, http_client


def safe_pdf_filename(title: str, year: int | None) -> str:
    # Barra em título não é diretório: troca por espaço antes de sanitizar.
    stem = sanitize_filename(re.sub(r"[\\/]", " ", title or "artigo"), max_stem=60)
    y = f"_{year}" if year else ""
    return f"{stem}{y}.pdf"


def download_pdf(
    url: str,
    dest_dir: Path,
    filename: str,
    *,
    client: httpx.Client | None = None,
    max_bytes: int = MAX_PDF_BYTES,
) -> Path:
    """Baixa o PDF com limite de tamanho e confere a assinatura %PDF.

    Grava com nome único (nome.pdf, nome_2.pdf...). A versão anterior usava
    sufixo fixo `_novo` e sobrescrevia se esse também existisse.
    """
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"URL inválida para download: {url!r}")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"}
    chunks: list[bytes] = []
    size = 0
    with http_client(client, 90.0) as http:
        with http.stream("GET", url, headers=headers) as r:
            r.raise_for_status()
            for chunk in r.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise RuntimeError(
                        f"PDF maior que {max_bytes // (1024 * 1024)} MB; "
                        "baixe manualmente e envie em Enviar documentos."
                    )
                chunks.append(chunk)
    data = b"".join(chunks)
    if not data.startswith(b"%PDF"):
        raise RuntimeError(
            "O link não devolveu um PDF (página HTML ou acesso restrito). "
            "Baixe o arquivo no site e use Enviar documentos."
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = unique_path(dest_dir, sanitize_filename(filename), Path.exists)
    dest.write_bytes(data)
    return dest
