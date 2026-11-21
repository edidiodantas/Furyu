import pytest
from paperqa.settings import PromptSettings

from ipeia_academico.academic_prompts import (
    ACADEMIC_QA_PROMPT,
    ACADEMIC_SYSTEM_PROMPT,
    DEFAULT_SECTIONS,
    Mode,
    WritingInputError,
    mode_params,
    parse_sections,
    section_request,
    summary_request,
    validate_theme,
)


def test_prompt_academico_e_aceito_pelo_paperqa():
    # PromptSettings valida as variáveis do template; falharia se usássemos outras.
    prompts = PromptSettings(system=ACADEMIC_SYSTEM_PROMPT, qa=ACADEMIC_QA_PROMPT)
    assert "{example_citation}" in prompts.qa
    assert "impessoal" in prompts.system


def test_mode_params():
    q = mode_params(Mode.QUESTION, question_length="300", question_evidence_k=10)
    s = mode_params(Mode.SUMMARY, question_length="300", question_evidence_k=10)
    t = mode_params(Mode.ACADEMIC_TEXT, question_length="300", question_evidence_k=20)
    assert (q.answer_length, q.evidence_k) == ("300", 10)
    assert s.evidence_k == 15 and "600" in s.answer_length
    assert t.evidence_k == 20  # nunca menos que o configurado


def test_summary_request():
    assert "Freire1987" in summary_request("Freire1987", "português")
    assert summary_request("X", "").endswith("conclusões, nessa ordem.")
    with pytest.raises(WritingInputError):
        summary_request("  ", "português")


def test_parse_sections():
    assert parse_sections("") == list(DEFAULT_SECTIONS)
    assert parse_sections(" Introdução \n\nMétodo\nIntrodução") == ["Introdução", "Método"]
    with pytest.raises(WritingInputError, match="máximo"):
        parse_sections("\n".join(f"S{i}" for i in range(11)))


def test_validate_theme():
    assert validate_theme("  avaliação   formativa  ") == "avaliação formativa"
    with pytest.raises(WritingInputError):
        validate_theme("curto")
    with pytest.raises(WritingInputError):
        validate_theme("x" * 1001)


def test_section_request_traz_plano_e_idioma():
    req = section_request("tema longo o bastante", "Método", ["Introdução", "Método"], "português")
    assert '"Método"' in req and "Introdução; Método" in req
    assert req.endswith("(Responda em português.)")
