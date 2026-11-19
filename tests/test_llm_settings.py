"""Garante que nenhum papel de LLM fica apontando para a OpenAI."""

from pathlib import Path

import pytest

pytest.importorskip("paperqa")

from ipeia_academico.config import load_config  # noqa: E402
from ipeia_academico.llm_settings import build_llm_config, build_settings  # noqa: E402


def test_llm_config_aponta_para_ollama():
    cfg = build_llm_config("ollama/m", api_base="http://h:1", temperature=0.0, provider="ollama")
    params = cfg["model_list"][0]["litellm_params"]
    assert params["model"] == "ollama/m"
    assert params["api_base"] == "http://h:1"
    assert params["temperature"] == 0.0


def test_llm_config_nuvem_sem_api_base_nem_temperature_nem_chave():
    cfg = build_llm_config("anthropic/claude-opus-5-5", provider="anthropic")
    params = cfg["model_list"][0]["litellm_params"]
    assert "api_base" not in params and "temperature" not in params
    assert not any("key" in k for k in params)  # chave fica só no ambiente


def test_os_quatro_papeis_usam_ollama(tmp_path):
    config = load_config({"OLLAMA_MODEL": "qwen3.5:4b", "PDF_DIR": str(tmp_path),
                          "PQA_HOME": str(tmp_path / "pqa")}, Path("/x"))
    s = build_settings(config)
    assert s.llm == s.summary_llm == s.agent.agent_llm == s.parsing.enrichment_llm == "ollama/qwen3.5:4b"
    for c in (s.llm_config, s.summary_llm_config, s.agent.agent_llm_config, s.parsing.enrichment_llm_config):
        assert c["model_list"][0]["litellm_params"]["api_base"] == "http://localhost:11434"
    assert s.embedding.startswith("st-")
    assert s.agent.index.paper_directory == str(tmp_path.resolve())


def test_troca_para_anthropic_nao_deixa_papel_na_openai(tmp_path):
    config = load_config({"LLM_PROVIDER": "anthropic", "LLM_MODEL": "claude-opus-5-5",
                          "SUMMARY_LLM_MODEL": "claude-haiku-5-5",
                          "PDF_DIR": str(tmp_path), "PQA_HOME": str(tmp_path / "pqa")}, Path("/x"))
    s = build_settings(config)
    assert s.llm == s.agent.agent_llm == s.parsing.enrichment_llm == "anthropic/claude-opus-5-5"
    assert s.summary_llm == "anthropic/claude-haiku-5-5"
    assert s.answer.max_concurrent_requests == 4


def test_embedding_ollama_recebe_api_base(tmp_path):
    config = load_config({"EMBEDDING_MODEL": "ollama/bge-m3", "PDF_DIR": str(tmp_path),
                          "PQA_HOME": str(tmp_path / "pqa")}, Path("/x"))
    s = build_settings(config)
    assert s.embedding == "ollama/bge-m3"
    assert s.embedding_config == {"kwargs": {"api_base": "http://localhost:11434"}}


def test_parametros_de_resposta(tmp_path):
    env = {"EVIDENCE_K": "20", "ANSWER_MAX_SOURCES": "8", "ANSWER_LENGTH": "cerca de 800 palavras",
           "PDF_DIR": str(tmp_path), "PQA_HOME": str(tmp_path / "pqa")}
    config = load_config(env, Path("/x"))
    a = build_settings(config).answer
    assert (a.evidence_k, a.answer_max_sources, a.answer_length) == (20, 8, "cerca de 800 palavras")
