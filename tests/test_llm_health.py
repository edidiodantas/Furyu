from pathlib import Path

from ipeia_academico.config import load_config
from ipeia_academico.llm_health import check_llm

ROOT = Path("/x")


def test_ollama_consulta_o_servidor():
    calls = []

    def fetch(url, timeout):
        calls.append(url)
        return {"models": [{"name": "llama3.2:3b"}]}

    cfg = load_config({"LLM_MODEL": "llama3.2:3b"}, ROOT)
    assert check_llm(cfg, {}, fetch=fetch).ok
    assert calls == ["http://localhost:11434/api/tags"]


def test_nuvem_sem_chave_avisa_e_nao_chama_rede():
    def fetch(url, timeout):  # pragma: no cover
        raise AssertionError("não deve chamar a rede")

    cfg = load_config({"LLM_PROVIDER": "anthropic", "LLM_MODEL": "claude-opus-5-5"}, ROOT)
    h = check_llm(cfg, {}, fetch=fetch)
    assert not h.ok and "ANTHROPIC_API_KEY" in h.message


def test_nuvem_com_chave_fica_pronta():
    cfg = load_config({"LLM_PROVIDER": "openrouter", "LLM_MODEL": "algum/modelo"}, ROOT)
    h = check_llm(cfg, {"OPENROUTER_API_KEY": "x"})
    assert h.ok and "openrouter/algum/modelo" in h.message
