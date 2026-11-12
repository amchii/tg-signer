import asyncio

import pytest
from click.testing import CliRunner

import tg_signer.cli.automation as automation_cli
import tg_signer.cli.monitor as monitor_cli
import tg_signer.cli.signer as signer_cli
from tg_signer.core import ChatFolderError, UserSigner


class DummyWorker:
    def __init__(self):
        self.calls = []

    def app_run(self, coroutine):
        asyncio.run(coroutine)

    async def list_folders(self):
        self.calls.append({"method": "list_folders"})

    async def login(self, num_of_dialogs, folder=None):
        self.calls.append(
            {
                "method": "login",
                "num_of_dialogs": num_of_dialogs,
                "folder": folder,
            }
        )

    async def run(self, num_of_dialogs, folder=None):
        self.calls.append(
            {
                "method": "run",
                "num_of_dialogs": num_of_dialogs,
                "folder": folder,
            }
        )

    async def run_once(self, num_of_dialogs, folder=None):
        self.calls.append(
            {
                "method": "run_once",
                "num_of_dialogs": num_of_dialogs,
                "folder": folder,
            }
        )


@pytest.fixture
def runner():
    return CliRunner()


@pytest.mark.parametrize(
    "factory",
    [signer_cli.get_signer, monitor_cli.get_monitor, automation_cli.get_automation],
)
def test_worker_factories_accept_explicit_loop(factory, tmp_path):
    loop = asyncio.new_event_loop()
    try:
        worker = factory(
            "task",
            {
                "account": "acct",
                "proxy": None,
                "session_dir": tmp_path,
                "workdir": tmp_path,
                "session_string": None,
                "in_memory": False,
            },
            loop=loop,
        )
        assert worker.loop is loop
    finally:
        loop.close()


def test_list_folders_command(monkeypatch, runner):
    worker = DummyWorker()
    monkeypatch.setattr(signer_cli, "get_signer", lambda *_args, **_kwargs: worker)

    result = runner.invoke(signer_cli.tg_signer, ["list-folders"])

    assert result.exit_code == 0
    assert worker.calls == [{"method": "list_folders"}]


@pytest.mark.parametrize(
    ("args", "method"),
    [
        (["login", "--from-folder", "Sign"], "login"),
        (["run", "--from-folder", "Sign", "task"], "run"),
        (["run-once", "--from-folder", "Sign", "task"], "run_once"),
        (
            [
                "multi-run",
                "--account",
                "account-a",
                "--from-folder",
                "Sign",
                "task",
            ],
            "run",
        ),
    ],
)
def test_signer_commands_forward_folder(monkeypatch, runner, args, method):
    worker = DummyWorker()
    monkeypatch.setattr(signer_cli, "get_signer", lambda *_args, **_kwargs: worker)

    result = runner.invoke(signer_cli.tg_signer, args)

    assert result.exit_code == 0, result.output
    assert worker.calls[0]["method"] == method
    assert worker.calls[0]["folder"] == "Sign"


@pytest.mark.parametrize(
    ("proxy", "port"),
    [
        ("socks4://localhost", 1080),
        ("socks5://localhost", 1080),
        ("http://localhost", 8080),
        ("socks5://localhost:7890", 7890),
    ],
)
def test_login_runs_with_kurigram_client(monkeypatch, runner, tmp_path, proxy, port):
    loops = []

    async def login(self, num_of_dialogs, folder=None):
        assert self.app.proxy.port == port
        assert asyncio.get_running_loop() is self.loop
        loops.append(asyncio.get_running_loop())

    monkeypatch.setattr(UserSigner, "login", login)
    result = runner.invoke(
        signer_cli.tg_signer,
        ["--workdir", str(tmp_path), "--proxy", proxy, "login"],
    )

    assert result.exit_code == 0, result.exception
    assert len(loops) == 1
    assert not loops[0].is_closed()


@pytest.mark.parametrize(
    ("args", "expected_tasks", "shared_client"),
    [
        (["run", "a", "b"], [("a", "main"), ("b", "main")], True),
        (
            ["multi-run", "-a", "first", "-a", "second", "task"],
            [("task", "first"), ("task", "second")],
            False,
        ),
    ],
)
def test_signer_batch_shares_one_loop(
    monkeypatch, runner, tmp_path, args, expected_tasks, shared_client
):
    tasks = []
    loops = []
    clients = []

    async def run(self, num_of_dialogs, folder=None):
        assert asyncio.get_running_loop() is self.loop
        tasks.append((self.task_name, self.app.name))
        clients.append(self.app)
        loops.append(asyncio.get_running_loop())
        await asyncio.sleep(0)
        assert len(tasks) == 2

    monkeypatch.setattr(UserSigner, "run", run)
    result = runner.invoke(
        signer_cli.tg_signer,
        ["--workdir", str(tmp_path), "--account", "main", *args],
        env={"TG_PROXY": None},
    )

    assert result.exit_code == 0, result.exception
    assert tasks == expected_tasks
    assert (clients[0] is clients[1]) is shared_client
    assert loops[0] is loops[1]
    assert not loops[0].is_closed()


@pytest.mark.parametrize(
    ("args", "module", "factory_name"),
    [
        (
            ["automation", "run", "--from-folder", "Sign", "task"],
            automation_cli,
            "get_automation",
        ),
        (
            ["monitor", "run", "--from-folder", "Sign", "task"],
            monitor_cli,
            "get_monitor",
        ),
    ],
)
def test_subsystem_run_commands_forward_folder(
    monkeypatch, runner, args, module, factory_name
):
    worker = DummyWorker()
    monkeypatch.setattr(module, factory_name, lambda *_args, **_kwargs: worker)

    result = runner.invoke(signer_cli.tg_signer, args)

    assert result.exit_code == 0, result.output
    assert worker.calls == [{"method": "run", "num_of_dialogs": 20, "folder": "Sign"}]


def test_folder_errors_are_reported_as_click_errors(monkeypatch, runner):
    class ErrorWorker(DummyWorker):
        async def login(self, num_of_dialogs, folder=None):
            del num_of_dialogs, folder
            raise ChatFolderError("folder error")

    worker = ErrorWorker()
    monkeypatch.setattr(signer_cli, "get_signer", lambda *_args, **_kwargs: worker)

    result = runner.invoke(
        signer_cli.tg_signer,
        ["login", "--from-folder", "Missing"],
    )

    assert result.exit_code == 1
    assert "Error: folder error" in result.output
