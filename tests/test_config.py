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
    assert cfg.ollama_model == DEFAULT_OLLAMA_MODEL
    assert cfg.llm_name == f"ollama/{DEFAULT_OLLAMA_MODEL}"
    assert cfg.ollama_base_url == "http://localhost:11434"
    assert cfg.pdf_dir == ROOT / "documentos"
    assert cfg.library_dir == ROOT / ".pqa" / "acervo"
    assert cfg.contact_email == ""


def test_caminho_absoluto_e_preservado(tmp_path):
    cfg = load_config({"PDF_DIR": str(tmp_path)}, ROOT)
    assert cfg.pdf_dir == tmp_path


def test_barra_final_da_url_e_removida():
    cfg = load_config({"OLLAMA_BASE_URL": "http://127.0.0.1:11434/"}, ROOT)
    assert cfg.ollama_base_url == "http://127.0.0.1:11434"


def test_url_sem_esquema_e_rejeitada():
    with pytest.raises(ConfigError):
        load_config({"OLLAMA_BASE_URL": "localhost:11434"}, ROOT)


def test_modelo_com_espaco_e_rejeitado():
    with pytest.raises(ConfigError):
        load_config({"OLLAMA_MODEL": "qwen 4b"}, ROOT)


def test_valores_em_branco_usam_padrao():
    cfg = load_config({"OLLAMA_MODEL": "   ", "PDF_DIR": ""}, ROOT)
    assert cfg.ollama_model == DEFAULT_OLLAMA_MODEL
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
