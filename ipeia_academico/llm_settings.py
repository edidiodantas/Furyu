"""Monta o `Settings` do PaperQA2 a partir da configuração (qualquer provedor).

Por que configurar os quatro papéis: o padrão do PaperQA2 para llm,
summary_llm, agent_llm e enrichment_llm é um modelo da OpenAI. Se qualquer um
ficar sem configuração, o PaperQA2 tenta essa API mesmo com outro provedor.
"""

from __future__ import annotations

from typing import Any

from paperqa import Settings
from paperqa.settings import (
    AgentSettings,
    AnswerSettings,
    IndexSettings,
    ParsingSettings,
    PromptSettings,
)

from ipeia_academico.academic_prompts import (
    ACADEMIC_QA_PROMPT,
    ACADEMIC_SYSTEM_PROMPT,
    Mode,
    mode_params,
)
from ipeia_academico.config import AppConfig

LLM_TIMEOUT_SECONDS = 600
AGENT_TIMEOUT_SECONDS = 1800.0


def build_llm_config(
    llm_name: str,
    *,
    api_base: str = "",
    temperature: float | None = None,
    provider: str = "",
) -> dict[str, Any]:
    """Config do LiteLLM Router para um modelo.

    A chave de API não entra aqui: o LiteLLM lê a variável padrão do
    provedor (ANTHROPIC_API_KEY, OPENAI_API_KEY...) do ambiente.
    """
    params: dict[str, Any] = {"model": llm_name, "timeout": LLM_TIMEOUT_SECONDS}
    if api_base:
        params["api_base"] = api_base
    if temperature is not None:
        params["temperature"] = temperature
    if provider == "ollama":
        params["api_type"] = "ollama"
    return {"model_list": [{"model_name": llm_name, "litellm_params": params}]}


def build_embedding_config(config: AppConfig) -> dict[str, Any] | None:
    """kwargs repassados ao litellm.aembedding (ex.: api_base do Ollama)."""
    api_base = config.embedding_api_base
    if not api_base and config.embedding_model.startswith("ollama/"):
        api_base = config.llm_api_base if config.provider.name == "ollama" else "http://localhost:11434"
    return {"kwargs": {"api_base": api_base}} if api_base else None


def build_settings(config: AppConfig) -> Settings:
    """Settings do PaperQA2 para o modo manual (Docs.aadd / Docs.aquery).

    `agent.index` só é usado se alguém rodar o modo agente (`pqa ask`) com
    estas mesmas Settings; o acervo do app é persistido por `library.py`.
    """
    common = {
        "api_base": config.llm_api_base,
        "temperature": config.llm_temperature,
        "provider": config.provider.name,
    }
    llm_config = build_llm_config(config.llm_name, **common)
    summary_config = build_llm_config(config.summary_llm_name, **common)

    return Settings(
        llm=config.llm_name,
        llm_config=llm_config,
        summary_llm=config.summary_llm_name,
        summary_llm_config=summary_config,
        embedding=config.embedding_model,
        embedding_config=build_embedding_config(config),
        temperature=config.llm_temperature if config.llm_temperature is not None else 0.0,
        agent=AgentSettings(
            agent_llm=config.llm_name,
            agent_llm_config=llm_config,
            timeout=AGENT_TIMEOUT_SECONDS,
            index=IndexSettings(
                paper_directory=str(config.pdf_dir.resolve()),
                index_directory=str((config.pqa_home / "indexes").resolve()),
                concurrency=1,
            ),
        ),
        parsing=ParsingSettings(
            enrichment_llm=config.llm_name,
            enrichment_llm_config=llm_config,
            multimodal=False,
        ),
        prompts=PromptSettings(system=ACADEMIC_SYSTEM_PROMPT, qa=ACADEMIC_QA_PROMPT),
        answer=AnswerSettings(
            # Local: 1 requisição por vez (GPU pequena). Remoto: paralelo acelera.
            max_concurrent_requests=1 if config.provider.is_local else 4,
            evidence_k=config.evidence_k,
            answer_max_sources=config.answer_max_sources,
            answer_length=config.answer_length,
        ),
    )


def settings_for_mode(base: Settings, config: AppConfig, mode: Mode) -> Settings:
    """Cópia das Settings com tamanho de resposta e nº de trechos do modo."""
    params = mode_params(
        mode, question_length=config.answer_length, question_evidence_k=config.evidence_k
    )
    settings = base.model_copy(deep=True)
    settings.answer.answer_length = params.answer_length
    settings.answer.evidence_k = params.evidence_k
    return settings
