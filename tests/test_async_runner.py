import asyncio

import pytest

from ipeia_academico.async_runner import BackgroundLoop


@pytest.fixture
def loop():
    bg = BackgroundLoop()
    yield bg
    bg.close()


def test_devolve_resultado(loop):
    async def soma(a, b):
        await asyncio.sleep(0)
        return a + b

    assert loop.run(soma(2, 3)) == 5


def test_reusa_o_mesmo_event_loop(loop):
    async def current():
        return id(asyncio.get_running_loop())

    assert loop.run(current()) == loop.run(current())


def test_propaga_excecao(loop):
    async def boom():
        raise ValueError("falhou")

    with pytest.raises(ValueError, match="falhou"):
        loop.run(boom())


def test_timeout(loop):
    async def lento():
        await asyncio.sleep(5)

    with pytest.raises(TimeoutError):
        loop.run(lento(), timeout=0.05)


def test_apos_close_recusa(loop):
    loop.close()

    async def nada():
        return 1

    with pytest.raises(RuntimeError, match="encerrado"):
        loop.run(nada())
