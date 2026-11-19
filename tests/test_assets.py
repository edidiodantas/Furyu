"""A logo IPeia é obrigatória em todos os projetos: garante que os arquivos existem."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["logo-ipeia.png", "favicon-ipeia.png"])
def test_logo_existe_e_e_png(name):
    path = ROOT / "assets" / name
    assert path.exists(), f"faltando {path}"
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
