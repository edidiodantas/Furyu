from pathlib import Path

import pytest

from ipeia_academico.config import (
    DEFAULT_OLLAMA_MODEL,
    ConfigError,
    is_valid_contact_email,
    load_config,
)

ROOT = Path("/projeto")


def test_defaults_quando_env_vazio():
    cfg = load_config({}, ROOT)
    assert cfg.provider.name == "ollama"
    assert cfg.llm_model == DEFAULT_OLLAMA_MODEL
    assert cfg.llm_name == f"ollama/{DEFAULT_OLLAMA_MODEL}"
    assert cfg.llm_api_base == "http://localhost:11434"
    assert cfg.llm_temperature == 0.0
    assert cfg.is_local
    assert cfg.pdf_dir == ROOT / "documentos"
    assert cfg.library_dir == ROOT / ".pqa" / "acervo"
    assert cfg.contact_email == ""


def test_caminho_absoluto_e_preservado(tmp_path):
    cfg = load_config({"PDF_DIR": str(tmp_path)}, ROOT)
    assert cfg.pdf_dir == tmp_path


def test_barra_final_da_url_e_removida():
    cfg = load_config({"OLLAMA_BASE_URL": "http://127.0.0.1:11434/"}, ROOT)
    assert cfg.llm_api_base == "http://127.0.0.1:11434"


def test_url_sem_esquema_e_rejeitada():
    with pytest.raises(ConfigError):
        load_config({"OLLAMA_BASE_URL": "localhost:11434"}, ROOT)


def test_modelo_com_espaco_e_rejeitado():
    with pytest.raises(ConfigError):
        load_config({"OLLAMA_MODEL": "qwen 4b"}, ROOT)


def test_valores_em_branco_usam_padrao():
    cfg = load_config({"OLLAMA_MODEL": "   ", "PDF_DIR": ""}, ROOT)
    assert cfg.llm_model == DEFAULT_OLLAMA_MODEL
    assert cfg.pdf_dir == ROOT / "documentos"


@pytest.mark.parametrize(
    "email, ok",
    [
        ("pesquisador@ufrn.br", True),
        ("pesquisa@suaescola.edu.br", False),  # placeholder do .env.example antigo
        ("seu.email@exemplo.com", False),
        ("sem-arroba", False),
        ("a@b", False),
        ("", False),
    ],
)
def test_validacao_de_email(email, ok):
    assert is_valid_contact_email(email) is ok


def test_email_placeholder_vira_vazio():
    cfg = load_config({"CONTACT_EMAIL": "pesquisa@suaescola.edu.br"}, ROOT)
    assert cfg.contact_email == ""


# --- troca de motor de IA -------------------------------------------------------
def test_llm_model_tem_prioridade_sobre_ollama_model():
    cfg = load_config({"LLM_MODEL": "llama3.2:3b", "OLLAMA_MODEL": "qwen3.5:4b"}, ROOT)
    assert cfg.llm_name == "ollama/llama3.2:3b"


def test_anthropic_sem_temperature_e_sem_api_base():
    cfg = load_config({"LLM_PROVIDER": "anthropic", "LLM_MODEL": "claude-opus-5-5"}, ROOT)
    assert cfg.llm_name == "anthropic/claude-opus-5-5"
    assert cfg.llm_api_base == ""
    assert cfg.llm_temperature is None
    assert not cfg.is_local


def test_anthropic_recusa_temperature():
    with pytest.raises(ConfigError, match="LLM_TEMPERATURE"):
        env = {"LLM_PROVIDER": "anthropic", "LLM_MODEL": "claude-opus-5-5", "LLM_TEMPERATURE": "0.2"}
        load_config(env, ROOT)


def test_provedor_na_nuvem_exige_modelo():
    with pytest.raises(ConfigError, match="LLM_MODEL"):
        load_config({"LLM_PROVIDER": "openai"}, ROOT)


def test_ollama_model_nao_vaza_para_outro_provedor():
    with pytest.raises(ConfigError, match="LLM_MODEL"):
        load_config({"LLM_PROVIDER": "gemini", "OLLAMA_MODEL": "qwen3.5:4b"}, ROOT)


def test_openai_compatible_exige_api_base():
    with pytest.raises(ConfigError, match="LLM_API_BASE"):
        load_config({"LLM_PROVIDER": "openai_compatible", "LLM_MODEL": "x"}, ROOT)
    cfg = load_config({"LLM_PROVIDER": "openai_compatible", "LLM_MODEL": "qwen",
                       "LLM_API_BASE": "http://localhost:1234/v1"}, ROOT)
    assert cfg.llm_name == "openai/qwen" and cfg.is_local


def test_provedor_invalido():
    with pytest.raises(ConfigError, match="LLM_PROVIDER inválido"):
        load_config({"LLM_PROVIDER": "skynet"}, ROOT)


def test_summary_model_proprio():
    cfg = load_config({"LLM_PROVIDER": "openai", "LLM_MODEL": "grande", "SUMMARY_LLM_MODEL": "pequeno"}, ROOT)
    assert cfg.summary_llm_name == "openai/pequeno"


def test_embedding_na_nuvem_torna_config_nao_local():
    cfg = load_config({"EMBEDDING_MODEL": "text-embedding-3-small"}, ROOT)
    assert cfg.embedding_is_remote and not cfg.is_local
    assert load_config({"EMBEDDING_MODEL": "ollama/bge-m3"}, ROOT).is_local


@pytest.mark.parametrize(
    "key, raw", [("EVIDENCE_K", "0"), ("EVIDENCE_K", "abc"), ("ANSWER_MAX_SOURCES", "999")]
)
def test_inteiros_invalidos(key, raw):
    with pytest.raises(ConfigError, match=key):
        load_config({key: raw}, ROOT)


def test_missing_api_key():
    from ipeia_academico.config import missing_api_key

    cfg = load_config({"LLM_PROVIDER": "anthropic", "LLM_MODEL": "claude-opus-5-5"}, ROOT)
    assert missing_api_key(cfg, {}) == "ANTHROPIC_API_KEY"
    assert missing_api_key(cfg, {"ANTHROPIC_API_KEY": "x"}) == ""
    assert missing_api_key(load_config({}, ROOT), {}) == ""
