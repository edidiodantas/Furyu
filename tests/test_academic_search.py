"""Testes da busca com httpx.MockTransport (sem rede real)."""

import httpx
import pytest

from ipeia_academico.search import (
    PaperHit,
    SearchError,
    download_pdf,
    parsing,
    resolve_pdf_url,
    safe_pdf_filename,
    search_academic,
)
from ipeia_academico.search.catalogs import search_crossref, search_oasisbr, search_semantic_scholar
from ipeia_academico.search.unpaywall import attach_unpaywall_pdfs


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def hit(**kw):
    base = dict(paper_id="p", title="T", year=2020, authors="", venue="", doi="",
                abstract="", pdf_url="", source="crossref")
    base.update(kw)
    return PaperHit(**base)


# --- funções puras ------------------------------------------------------------
@pytest.mark.parametrize(
    "url, ok",
    [
        ("https://x.org/a.pdf", True),
        ("https://www.scielo.br/scielo.php?script=sci_pdf&pid=1", True),
        ("https://doi.org/10.1/x.pdf", False),
        ("ftp://x/a.pdf", False),
        ("https://x.org/artigo", False),
    ],
)
def test_looks_like_pdf_url(url, ok):
    assert parsing.looks_like_pdf_url(url) is ok


def test_pid_scielo_com_issn_terminado_em_x():
    # Antes o regex exigia só dígitos no ISSN e perdia PIDs como este.
    pid = parsing.scielo_pid("http://www.scielo.br/?pid=S0102-311X2006000100001")
    assert pid == "S0102-311X2006000100001"
    assert parsing.year_from_pid(pid) == 2006


def test_first_doi_remove_pontuacao_final():
    assert parsing.first_doi("veja https://doi.org/10.1590/abc.123).") == "10.1590/abc.123"


def test_safe_pdf_filename():
    assert safe_pdf_filename("Educação: um estudo/2", 2021) == "Educacao_um_estudo_2_2021.pdf"
    assert safe_pdf_filename("", None) == "artigo.pdf"


def test_dedupe_por_doi():
    hits = [hit(doi="10.1/A"), hit(doi="10.1/a", paper_id="q"), hit(doi="", paper_id="")]
    assert len(parsing.dedupe(hits)) == 1


# --- catálogos ----------------------------------------------------------------
def test_oasisbr_extrai_doi_pid_e_pdf():
    def handler(request):
        assert request.url.host == "oasisbr.ibict.br"
        return httpx.Response(200, json={"records": [{
            "id": "rec1",
            "title": " Educação inclusiva ",
            "authors": {"primary": {"Silva, Ana [Autor]": {}}},
            "urls": [{"url": "http://www.scielo.br/scielo.php?script=sci_arttext&pid=S0101-32622019000100001"},
                     {"url": "https://repo.br/bitstream/1/artigo.pdf"}],
        }]})

    with client_for(handler) as c:
        [h] = search_oasisbr("educação", client=c)
    assert h.title == "Educação inclusiva"
    assert h.authors == "Silva, Ana"
    assert h.doi == "10.1590/S0101-32622019000100001"
    assert h.year == 2019
    assert h.pdf_url == "https://repo.br/bitstream/1/artigo.pdf"
    assert h.source == "scielo"


def test_oasisbr_refaz_sem_filtro_quando_vazio():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"records": []})

    with client_for(handler) as c:
        assert search_oasisbr("x", client=c) == []
    assert len(calls) == 2
    assert "format%3Aarticle" in calls[0] and "format" not in calls[1]


def test_semantic_scholar_tenta_de_novo_apos_429():
    responses = iter([
        httpx.Response(429),
        httpx.Response(200, json={"data": [{"paperId": "s2", "title": "Paper", "year": 2023,
                                            "externalIds": {"DOI": "10.1/x"},
                                            "openAccessPdf": {"url": "https://a.org/p.pdf"}}]}),
    ])
    sleeps = []
    with client_for(lambda r: next(responses)) as c:
        [h] = search_semantic_scholar("x", client=c, sleep=sleeps.append)
    assert sleeps == [1.5]
    assert h.pdf_url == "https://a.org/p.pdf" and h.doi == "10.1/x"


def test_semantic_scholar_429_duas_vezes_levanta():
    with client_for(lambda r: httpx.Response(429)) as c:
        with pytest.raises(RuntimeError, match="Semantic Scholar"):
            search_semantic_scholar("x", client=c, sleep=lambda s: None)


def test_crossref_remove_html_do_resumo_e_usa_mailto():
    def handler(request):
        assert request.url.params["mailto"] == "eu@ufrn.br"
        return httpx.Response(200, json={"message": {"items": [{
            "DOI": "10.1/c", "title": ["Título"], "abstract": "<jats:p>Resumo</jats:p>",
            "published": {"date-parts": [[2018, 5]]},
            "author": [{"given": "Ana", "family": "Silva"}],
        }]}})

    with client_for(handler) as c:
        [h] = search_crossref("x", email="eu@ufrn.br", client=c)
    assert h.abstract == "Resumo" and h.year == 2018 and h.authors == "Ana Silva"


# --- orquestração -------------------------------------------------------------
def test_search_academic_cai_para_crossref_quando_outros_falham():
    def handler(request):
        if request.url.host == "api.crossref.org":
            return httpx.Response(200, json={"message": {"items": [{"DOI": "10.1/c", "title": ["C"]}]}})
        return httpx.Response(503)

    with client_for(handler) as c:
        hits, note = search_academic("tema", client=c)
    assert [h.doi for h in hits] == ["10.1/c"]
    assert note.startswith("Crossref")
    assert "Oasisbr (IBICT) indisponível" in note


def test_search_academic_todos_falham_levanta_search_error():
    with client_for(lambda r: httpx.Response(500)) as c:
        with pytest.raises(SearchError):
            search_academic("tema", client=c)


def test_search_academic_consulta_vazia():
    assert search_academic("   ") == ([], "")


def test_unpaywall_email_recusado_nao_derruba_a_busca():
    # Bug antigo: o 422 do Unpaywall cancelava a busca inteira.
    def handler(request):
        if request.url.host == "oasisbr.ibict.br":
            return httpx.Response(200, json={"records": [{"id": "1", "title": "A",
                                                          "urls": [{"url": "https://doi.org/10.1234/a"}]}]})
        if request.url.host == "api.unpaywall.org":
            return httpx.Response(422)
        return httpx.Response(500)

    with client_for(handler) as c:
        hits, note = search_academic("tema", email="eu@ufrn.br", client=c)
    assert len(hits) == 1
    assert "Unpaywall recusou" in note


def test_attach_unpaywall_preenche_pdf():
    def handler(request):
        assert request.url.params["email"] == "eu@ufrn.br"
        return httpx.Response(200, json={"best_oa_location": {"url_for_pdf": "https://oa.org/x.pdf"}})

    hits = [hit(doi="10.1/x")]
    with client_for(handler) as c:
        assert attach_unpaywall_pdfs(hits, "eu@ufrn.br", client=c) == ""
    assert hits[0].pdf_url == "https://oa.org/x.pdf"
    assert hits[0].source == "crossref+unpaywall"


def test_attach_unpaywall_sem_email_nao_consulta():
    def handler(request):  # pragma: no cover - não deve ser chamado
        raise AssertionError("não deveria consultar")

    with client_for(handler) as c:
        assert attach_unpaywall_pdfs([hit(doi="10.1/x")], "", client=c) == ""


def test_resolve_pdf_url_usa_scielo_pelo_pid():
    h = hit(doi="10.1590/S0101-32622019000100001")

    with client_for(lambda r: httpx.Response(404)) as c:
        url = resolve_pdf_url(h, "eu@ufrn.br", client=c)
    assert "script=sci_pdf" in url and "S0101-32622019000100001" in url


# --- download -----------------------------------------------------------------
def test_download_pdf_grava_com_nome_unico(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF antigo")
    (tmp_path / "a_2.pdf").write_bytes(b"%PDF antigo 2")
    with client_for(lambda r: httpx.Response(200, content=b"%PDF-1.7 novo")) as c:
        dest = download_pdf("https://x.org/a.pdf", tmp_path, "a.pdf", client=c)
    assert dest.name == "a_3.pdf"
    assert (tmp_path / "a.pdf").read_bytes() == b"%PDF antigo"  # não sobrescreveu


def test_download_rejeita_html(tmp_path):
    with client_for(lambda r: httpx.Response(200, content=b"<html>login</html>")) as c:
        with pytest.raises(RuntimeError, match="não devolveu um PDF"):
            download_pdf("https://x.org/a.pdf", tmp_path, "a.pdf", client=c)
    assert list(tmp_path.iterdir()) == []


def test_download_respeita_limite_de_tamanho(tmp_path):
    with client_for(lambda r: httpx.Response(200, content=b"%PDF" + b"0" * 100)) as c:
        with pytest.raises(RuntimeError, match="maior que"):
            download_pdf("https://x.org/a.pdf", tmp_path, "a.pdf", client=c, max_bytes=50)


def test_download_rejeita_esquema_invalido(tmp_path):
    with pytest.raises(ValueError):
        download_pdf("file:///etc/passwd", tmp_path, "a.pdf")
