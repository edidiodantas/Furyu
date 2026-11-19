import pytest

from ipeia_academico.providers import PROVIDERS, UnknownProviderError, get_provider, litellm_model_name


def test_todos_os_provedores_tem_prefixo_litellm():
    for p in PROVIDERS.values():
        assert p.litellm_prefix.endswith("/")


def test_get_provider_ignora_caixa_e_espacos():
    assert get_provider("  Anthropic ").name == "anthropic"


def test_get_provider_invalido():
    with pytest.raises(UnknownProviderError):
        get_provider("x")


def test_prefixo_nao_duplica():
    p = get_provider("ollama")
    assert litellm_model_name(p, "llama3.2:3b") == "ollama/llama3.2:3b"
    assert litellm_model_name(p, "ollama/llama3.2:3b") == "ollama/llama3.2:3b"


def test_chaves_vem_de_variaveis_padrao():
    assert get_provider("anthropic").api_key_env == "ANTHROPIC_API_KEY"
    assert get_provider("ollama").api_key_env == ""
