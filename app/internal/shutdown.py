import asyncio
import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.internal.logging import logger

_shutdown_event = asyncio.Event()


def is_shutting_down() -> bool:
    return _shutdown_event.is_set()


def _handle_signal(sig: int) -> None:
    logger.info("shutdown.signal_received", signal=sig)
    _shutdown_event.set()


@asynccontextmanager
async def lifespan_signals() -> AsyncIterator[None]:
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except NotImplementedError:
            pass
    try:
        yield
    finally:
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.remove_signal_handler(sig)
            except (NotImplementedError, ValueError):
                pass
