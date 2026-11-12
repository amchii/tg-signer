import asyncio

import pytest
from pyrogram.session import Session

from tests.telegram import TelegramServer
from tg_signer.core import UserSigner


def _clear_core_client_state():
    import tg_signer.core as core

    core._CLIENT_INSTANCES.clear()
    core._CLIENT_REFS.clear()
    core._CLIENT_ASYNC_LOCKS.clear()
    core._LOGIN_ASYNC_LOCKS.clear()
    core._LOGIN_USERS.clear()
    core._API_ASYNC_LOCKS.clear()
    core._API_LAST_CALL_AT.clear()


@pytest.fixture(autouse=True)
def clear_core_client_state():
    _clear_core_client_state()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield
    finally:
        _clear_core_client_state()
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()
        asyncio.set_event_loop(None)


@pytest.fixture
def signer_factory(tmp_path):
    def factory(
        *,
        cls=UserSigner,
        task_name="task",
        account="acct",
        session_dir=None,
        workdir=None,
        **kwargs,
    ):
        return cls(
            task_name=task_name,
            account=account,
            session_dir=session_dir or tmp_path,
            workdir=workdir or tmp_path / ".signer",
            **kwargs,
        )

    return factory


@pytest.fixture
def telegram_server(monkeypatch):
    server = TelegramServer()

    async def start(session):
        server.started.append(session)
        session.is_started.set()

    async def stop(session):
        server.stopped.append(session)
        session.is_started.clear()

    async def invoke(session, query, **kwargs):
        return await server.invoke(query)

    monkeypatch.setattr(Session, "start", start)
    monkeypatch.setattr(Session, "stop", stop)
    monkeypatch.setattr(Session, "invoke", invoke)
    return server
