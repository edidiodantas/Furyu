"""Instruções (prompts) e parâmetros dos modos de escrita acadêmica.

Funções puras: só montam textos. Quem chama o PaperQA2 é o serviço.

O prompt de resposta (`qa`) do PaperQA2 só aceita as variáveis {context},
{question}, {example_citation}, {prior_answer_prompt} e {answer_length}
(validado por PromptSettings). As chaves de citação continuam no formato do
PaperQA2; a conversão para ABNT é feita depois, em `citations.py`, porque o
código acerta a formatação e o modelo pequeno não.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

MAX_SECTIONS = 10
MAX_THEME_CHARS = 1000
DEFAULT_SECTIONS = ("Introdução", "Desenvolvimento", "Considerações finais")

ACADEMIC_SYSTEM_PROMPT = (
    "Você é um assistente de pesquisa acadêmica. Escreva em português do Brasil, "
    "na norma culta, em linguagem impessoal (terceira pessoa), objetiva e formal, "
    "como em um artigo científico. Use apenas as informações do contexto fornecido; "
    "não invente dados, autores, datas nem páginas. Quando o contexto não bastar, "
    "diga isso claramente."
)

ACADEMIC_QA_PROMPT = (
    "Responda à solicitação abaixo usando somente o contexto.\n\n"
    "Contexto:\n\n{context}\n\n---\n\n"
    "Solicitação: {question}\n\n"
    "Escreva em parágrafos coesos, com frases claras e encadeamento lógico. "
    "Ao final de cada frase que use uma fonte, indique a chave de citação do "
    "trecho entre parênteses, exatamente como aparece no contexto, por exemplo "
    "{example_citation}. Use só chaves que estão no contexto e não junte chaves. "
    "Não escreva lista de referências: ela é gerada automaticamente. "
    "Se o contexto não tiver informação suficiente, responda "
    '"Não é possível responder com base no acervo."\n\n'
    "{prior_answer_prompt}"
    "Texto ({answer_length}):"
)


class Mode(str, Enum):
    QUESTION = "pergunta"
    SUMMARY = "resumo"
    ACADEMIC_TEXT = "texto"


@dataclass(frozen=True)
class ModeParams:
    answer_length: str
    evidence_k: int


class WritingInputError(ValueError):
    """Tema, seções ou documento inválidos."""


def mode_params(mode: Mode, *, question_length: str, question_evidence_k: int) -> ModeParams:
    """Resumo e seções leem mais trechos e escrevem mais que uma pergunta."""
    if mode is Mode.SUMMARY:
        return ModeParams("cerca de 600 palavras", max(question_evidence_k, 15))
    if mode is Mode.ACADEMIC_TEXT:
        return ModeParams("cerca de 400 palavras", max(question_evidence_k, 12))
    return ModeParams(question_length, question_evidence_k)


def summary_request(document_label: str, language: str) -> str:
    """Pedido de resumo de um documento (busca restrita a ele)."""
    label = " ".join((document_label or "").split())
    if not label:
        raise WritingInputError("Escolha o documento a resumir.")
    request = (
        f"Faça um resumo acadêmico do documento {label}: apresente o objetivo, "
        "a abordagem ou metodologia, os principais argumentos ou resultados e as "
        "conclusões, nessa ordem."
    )
    return f"{request}\n\n(Responda em {language}.)" if language else request


def parse_sections(raw: str) -> list[str]:
    """Uma seção por linha; vazio usa Introdução/Desenvolvimento/Considerações."""
    sections = [" ".join(line.split()) for line in (raw or "").splitlines()]
    sections = list(dict.fromkeys(s for s in sections if s))
    if not sections:
        return list(DEFAULT_SECTIONS)
    if len(sections) > MAX_SECTIONS:
        raise WritingInputError(f"Use no máximo {MAX_SECTIONS} seções.")
    return sections


def validate_theme(theme: str) -> str:
    theme = " ".join((theme or "").split())
    if len(theme) < 10:
        raise WritingInputError("Descreva o tema com pelo menos 10 caracteres.")
    if len(theme) > MAX_THEME_CHARS:
        raise WritingInputError(f"Tema longo demais (máximo {MAX_THEME_CHARS} caracteres).")
    return theme


def section_request(theme: str, section: str, sections: list[str], language: str) -> str:
    """Pedido para escrever uma seção, sabendo do plano completo do texto.

    Informar o plano evita que a Introdução antecipe as conclusões e que o
    Desenvolvimento repita a Introdução.
    """
    plan = "; ".join(sections)
    request = (
        f"Escreva a seção \"{section}\" de um texto acadêmico sobre: {theme}. "
        f"O texto completo terá as seções: {plan}. Escreva somente o conteúdo "
        "desta seção, sem repetir o título dela e sem tratar do que cabe às outras."
    )
    return f"{request}\n\n(Responda em {language}.)" if language else request
