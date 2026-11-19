"""Executa corrotinas a partir do código síncrono do Streamlit.

A versão anterior criava um event loop novo a cada chamada (`asyncio.run` em
outra thread). Objetos do PaperQA2/LiteLLM reaproveitados entre chamadas
(o mesmo `Docs`) podem guardar recursos presos ao loop que os criou. Aqui
um único loop vive numa thread dedicada durante toda a vida do app.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


class BackgroundLoop:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="ipeia-academico-async", daemon=True
        )
        self._thread.start()

    @property
    def is_running(self) -> bool:
        return self._thread.is_alive() and not self._loop.is_closed()

    def run(self, coro: Coroutine[Any, Any, T], timeout: float | None = None) -> T:
        """Bloqueia até a corrotina terminar e devolve o resultado (ou relança o erro)."""
        if not self.is_running:
            coro.close()
            raise RuntimeError("O executor assíncrono já foi encerrado.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise

    def close(self) -> None:
        if self._loop.is_closed():
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        self._loop.close()
