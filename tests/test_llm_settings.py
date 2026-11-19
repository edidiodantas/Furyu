"""Garante que nenhum papel de LLM fica apontando para a OpenAI."""

from pathlib import Path

import pytest

pytest.importorskip("paperqa")

from ipeia_academico.config import load_config  # noqa: E402
from ipeia_academico.llm_settings import build_ollama_llm_config, build_settings  # noqa: E402


def test_llm_config_aponta_para_ollama():
    cfg = build_ollama_llm_config("ollama/m", "http://h:1")
    params = cfg["model_list"][0]["litellm_params"]
    assert params["model"] == "ollama/m"
    assert params["api_base"] == "http://h:1"


def test_os_quatro_papeis_usam_ollama(tmp_path):
    config = load_config({"OLLAMA_MODEL": "qwen3.5:4b", "PDF_DIR": str(tmp_path),
                          "PQA_HOME": str(tmp_path / "pqa")}, Path("/x"))
    s = build_settings(config)
    assert s.llm == s.summary_llm == s.agent.agent_llm == s.parsing.enrichment_llm == "ollama/qwen3.5:4b"
    for c in (s.llm_config, s.summary_llm_config, s.agent.agent_llm_config, s.parsing.enrichment_llm_config):
        assert c["model_list"][0]["litellm_params"]["api_base"] == "http://localhost:11434"
    assert s.embedding.startswith("st-")
    assert s.agent.index.paper_directory == str(tmp_path.resolve())
