import pytest

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
    yield
    _clear_core_client_state()


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
