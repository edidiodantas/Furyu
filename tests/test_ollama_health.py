import urllib.error

import pytest

from ipeia_academico.ollama_health import check_ollama, model_is_installed


def fake_fetch(payload=None, exc=None):
    def _fetch(url, timeout):
        assert url == "http://localhost:11434/api/tags"
        if exc:
            raise exc
        return payload

    return _fetch


def test_modelo_instalado():
    h = check_ollama("http://localhost:11434", "qwen3.5:4b",
                     fetch=fake_fetch({"models": [{"name": "qwen3.5:4b"}]}))
    assert h.ok


def test_modelo_ausente_lista_disponiveis():
    h = check_ollama("http://localhost:11434", "qwen3.5:4b",
                     fetch=fake_fetch({"models": [{"name": "llama3.2:latest"}]}))
    assert not h.ok
    assert "ollama pull qwen3.5:4b" in h.message
    assert "llama3.2:latest" in h.message


def test_sem_modelos():
    h = check_ollama("http://localhost:11434", "x", fetch=fake_fetch({"models": []}))
    assert not h.ok and "nenhum modelo" in h.message


def test_servidor_fora_do_ar():
    h = check_ollama("http://localhost:11434", "x",
                     fetch=fake_fetch(exc=urllib.error.URLError("Connection refused")))
    assert not h.ok and "inacessível" in h.message


def test_json_invalido():
    h = check_ollama("http://localhost:11434", "x", fetch=fake_fetch(exc=ValueError("json")))
    assert not h.ok


@pytest.mark.parametrize(
    "model, installed, ok",
    [
        ("qwen3.5", ["qwen3.5:latest"], True),
        ("qwen3.5:4b", ["qwen3.5:4b"], True),
        ("qwen3.5:4b", ["qwen3.5:4b-instruct"], False),
        ("qwen3.5:4b", ["qwen3.5:9b"], False),
    ],
)
def test_model_is_installed(model, installed, ok):
    assert model_is_installed(model, installed) is ok
