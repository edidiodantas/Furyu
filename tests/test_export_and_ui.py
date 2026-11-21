from datetime import datetime
from types import SimpleNamespace

from ipeia_academico.export import answer_to_markdown, extract_answer_text, extract_references
from ipeia_academico.ui_helpers import escape_markdown, format_score, hit_button_key


def test_extract_answer_prefere_formatted_answer():
    s = SimpleNamespace(formatted_answer="F", answer="A")
    assert extract_answer_text(s) == "F"


def test_extract_answer_cai_para_answer_e_str():
    assert extract_answer_text(SimpleNamespace(formatted_answer="", answer="A")) == "A"
    assert extract_answer_text("bruto") == "bruto"


def test_extract_references():
    assert extract_references(SimpleNamespace(references=" Silva 2020 ")) == "Silva 2020"
    assert extract_references(SimpleNamespace()) == ""


def test_markdown_contem_pergunta_resposta_e_referencias():
    md = answer_to_markdown("Pergunta?", "Resposta (Silva 2020).", "1. Silva 2020",
                            model="qwen3.5:4b", generated_at=datetime(2026, 11, 19, 10, 30))
    assert "## Pergunta\n\nPergunta?" in md
    assert "## Referências\n\n1. Silva 2020" in md
    assert "2026-11-19 10:30" in md
    assert "Confira cada citação" in md


def test_markdown_nao_duplica_referencias_ja_na_resposta():
    md = answer_to_markdown("P", "Texto\n\nReferences\n1. X", "1. X",
                            model="m", generated_at=datetime(2026, 1, 1))
    assert "## Referências" not in md


def test_hit_button_key_unica_com_ids_vazios_e_titulos_iguais():
    hits = [
        SimpleNamespace(paper_id="", doi="", title="Artigo"),
        SimpleNamespace(paper_id="", doi="", title="Artigo"),
        SimpleNamespace(paper_id="", doi="10.1/x", title="Outro"),
        SimpleNamespace(paper_id="", doi="", title="Título/com: especiais!"),
    ]
    keys = [hit_button_key(i, h) for i, h in enumerate(hits)]
    assert len(set(keys)) == len(keys)
    assert all(k.replace("-", "").replace("_", "").isalnum() for k in keys)


def test_escape_markdown_neutraliza_links():
    assert escape_markdown("[x](javascript:alert)") == "\\[x\\]\\(javascript:alert\\)"


def test_format_score():
    assert format_score(8) == "8"
    assert format_score(None) == ""


def test_document_to_markdown_com_referencias_e_aviso():
    from ipeia_academico.export import document_to_markdown

    md = document_to_markdown(
        "Resumo", "Resumo de  X", "Corpo (Silva, 2020).", ("SILVA, A. **T**. 2020.",),
        model="m", generated_at=datetime(2026, 1, 2, 3, 4), missing_docnames=("Doc1",),
    )
    assert md.startswith("# Resumo\n")
    assert "- **Pedido:** Resumo de X" in md
    assert "## REFERÊNCIAS\n\nSILVA, A. **T**. 2020.\n" in md
    assert "Doc1" in md


def test_document_to_markdown_sem_referencias():
    from ipeia_academico.export import document_to_markdown

    md = document_to_markdown("T", "p", "b", (), model="m", generated_at=datetime(2026, 1, 2))
    assert "REFERÊNCIAS" not in md and "Sem dados ABNT" not in md
