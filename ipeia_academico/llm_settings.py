"""Monta o `Settings` do PaperQA2 apontando todos os papéis de LLM para o Ollama.

Por que os quatro papéis: o padrão do PaperQA2 para llm, summary_llm,
agent_llm e enrichment_llm é um modelo da OpenAI. Se qualquer um ficar sem
configuração, o PaperQA2 tenta a API paga (e falha sem chave).
"""

from __future__ import annotations

from typing import Any

from paperqa import Settings
from paperqa.settings import AgentSettings, AnswerSettings, IndexSettings, ParsingSettings

from ipeia_academico.config import AppConfig

LLM_TIMEOUT_SECONDS = 600
AGENT_TIMEOUT_SECONDS = 1800.0


def build_ollama_llm_config(llm_name: str, base_url: str) -> dict[str, Any]:
    """Config do LiteLLM Router para o Ollama local."""
    return {
        "model_list": [
            {
                "model_name": llm_name,
                "litellm_params": {
                    "model": llm_name,
                    "api_base": base_url,
                    "api_type": "ollama",
                    "timeout": LLM_TIMEOUT_SECONDS,
                    "temperature": 0.0,
                },
            }
        ]
    }


def build_settings(config: AppConfig) -> Settings:
    """Settings 100% locais: Ollama (LLM) + sentence-transformers (embeddings).

    Observação: o app usa `Docs.aadd`/`Docs.aquery` (modo manual, sem agente).
    `agent.index` só é usado se alguém rodar o modo agente (`pqa ask`) com
    estas mesmas Settings; o acervo do app é persistido por `library.py`.
    """
    llm_name = config.llm_name
    llm_config = build_ollama_llm_config(llm_name, config.ollama_base_url)

    return Settings(
        llm=llm_name,
        llm_config=llm_config,
        summary_llm=llm_name,
        summary_llm_config=llm_config,
        embedding=config.embedding_model,
        agent=AgentSettings(
            agent_llm=llm_name,
            agent_llm_config=llm_config,
            timeout=AGENT_TIMEOUT_SECONDS,
            index=IndexSettings(
                paper_directory=str(config.pdf_dir.resolve()),
                index_directory=str((config.pqa_home / "indexes").resolve()),
                concurrency=1,
            ),
        ),
        parsing=ParsingSettings(
            # Sem isto, figuras/tabelas seriam descritas por um modelo da OpenAI.
            enrichment_llm=llm_name,
            enrichment_llm_config=llm_config,
            multimodal=False,
        ),
        answer=AnswerSettings(max_concurrent_requests=1),
    )
