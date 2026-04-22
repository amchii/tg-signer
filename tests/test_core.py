import asyncio
import json
import pathlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from tg_signer.config import (
    ClickKeyboardByTextAction,
    SendTextAction,
    SignChatV3,
    SignConfigV3,
)
from tg_signer.core import (
    BaseUserWorker,
    ChatType,
    chat_has_forum_topics,
    get_client,
    readable_chat,
)


class TestBaseUserWorker:
    def test_initializes_defaults(self, signer_factory):
        worker = signer_factory(cls=BaseUserWorker, task_name=None)

        assert worker.task_name == "my_task"
        assert worker.context == {}
        assert worker.app.key.endswith("/acct")


def collect_outputs(monkeypatch, core):
    outputs = []

    def fake_print_to_user(message=""):
        outputs.append(message)

    monkeypatch.setattr(core, "print_to_user", fake_print_to_user)
    return outputs


def patch_client_methods(
    monkeypatch,
    core,
    *,
    start=None,
    stop=None,
    get_me=None,
    get_dialogs=None,
    save_session_string=None,
):
    async def fake_start(self):
        await asyncio.sleep(0)

    async def fake_stop(self):
        await asyncio.sleep(0)

    async def fake_get_me(self):
        await asyncio.sleep(0)
        return SimpleNamespace(id=123456)

    async def fake_get_dialogs(self, limit):
        del limit
        for _ in ():
            yield

    async def fake_save_session_string(self):
        await asyncio.sleep(0)

    monkeypatch.setattr(core.Client, "start", start or fake_start)
    monkeypatch.setattr(core.Client, "stop", stop or fake_stop)
    monkeypatch.setattr(core.Client, "get_me", get_me or fake_get_me)
    monkeypatch.setattr(core.Client, "get_dialogs", get_dialogs or fake_get_dialogs)
    monkeypatch.setattr(
        core.Client,
        "save_session_string",
        save_session_string or fake_save_session_string,
    )


def setup_login_test(monkeypatch, core, dialogs):
    async def fake_get_dialogs(self, limit):
        del limit
        for chat in dialogs:
            yield SimpleNamespace(chat=chat)

    patch_client_methods(monkeypatch, core, get_dialogs=fake_get_dialogs)
    return collect_outputs(monkeypatch, core)


def test_get_client_caching(tmp_path):
    """get_client should return the same instance for the same key and different
    instances for different keys.
    """
    import tg_signer.core as core

    name = "acct"
    client1 = get_client(name=name, workdir=tmp_path)
    client2 = get_client(name=name, workdir=tmp_path)
    assert client1 is client2

    # different name -> different key -> different instance
    client3 = get_client(name="other", workdir=tmp_path)
    assert client3 is not client1

    key = str(pathlib.Path(tmp_path).joinpath(name).resolve())
    assert key in core._CLIENT_INSTANCES


def test_get_client_isolated_by_workdir(tmp_path):
    client1 = get_client(name="acct", workdir=tmp_path / "one")
    client2 = get_client(name="acct", workdir=tmp_path / "two")

    assert client1 is not client2
    assert client1.key != client2.key


@pytest.mark.parametrize(
    ("chat_type", "expected"),
    [
        pytest.param(ChatType.FORUM, "论坛群组", id="forum"),
        pytest.param(ChatType.DIRECT, "频道私信", id="direct"),
    ],
)
def test_readable_chat_supports_new_chat_types(chat_type, expected):
    chat = SimpleNamespace(
        id=-2001,
        title="test-chat",
        type=chat_type,
        username=None,
        first_name=None,
    )

    assert f"type: {expected}" in readable_chat(chat)


@pytest.mark.parametrize(
    ("chat", "expected"),
    [
        pytest.param(
            SimpleNamespace(type="private", is_forum=False),
            False,
            id="private",
        ),
        pytest.param(
            SimpleNamespace(type=None, is_forum=False),
            False,
            id="unknown",
        ),
    ],
)
def test_chat_has_forum_topics_returns_false_for_non_forum_chat(chat, expected):
    assert chat_has_forum_topics(chat) is expected


@pytest.mark.parametrize(
    "chat",
    [
        pytest.param(
            SimpleNamespace(type=ChatType.SUPERGROUP, is_forum=True),
            id="forum-supergroup",
        ),
        pytest.param(
            SimpleNamespace(type=ChatType.FORUM, is_forum=False),
            id="forum",
        ),
    ],
)
def test_chat_has_forum_topics_returns_true_for_forum_chat(chat):
    assert chat_has_forum_topics(chat) is True


def test_chat_has_forum_topics_returns_false_for_direct_chat():
    chat = SimpleNamespace(type=ChatType.DIRECT, is_forum=False)

    assert chat_has_forum_topics(chat) is False


@pytest.mark.asyncio
async def test_client_context_manager_reference_counting_and_start_stop(
    monkeypatch, tmp_path
):
    """Test that entering/exiting the async context manager updates reference
    counts, calls start only once for nested entries, and calls stop after
    the final exit. We monkeypatch start/stop to avoid network operations.
    """
    import tg_signer.core as core

    start_stop_calls = []

    async def fake_start(self):
        # small yield to ensure proper async behavior
        await asyncio.sleep(0)
        start_stop_calls.append("start")
        self._fake_started = True

    async def fake_stop(self):
        await asyncio.sleep(0)
        start_stop_calls.append("stop")
        self._fake_started = False

    monkeypatch.setattr(core.Client, "start", fake_start)
    monkeypatch.setattr(core.Client, "stop", fake_stop)

    name = "acct"
    client = get_client(
        name=name,
        workdir=tmp_path,
    )
    key = client.key
    assert len(core._CLIENT_INSTANCES) == 1
    assert key in core._CLIENT_INSTANCES

    # enter outer context
    async with client as c1:
        assert c1 is client
        # refcount should be 1
        assert core._CLIENT_REFS[key] == 1
        assert getattr(client, "_fake_started", False) is True

        # nested enter should not call start again
        async with client as c2:
            assert c2 is client
            assert core._CLIENT_REFS[key] == 2
            assert getattr(client, "_fake_started", False) is True

        # after inner exit refcount back to 1 and still started
        assert core._CLIENT_REFS[key] == 1
        assert getattr(client, "_fake_started", False) is True

    # after outer exit refcount should be 0 and stop should have been called
    assert core._CLIENT_REFS[key] == 0
    assert getattr(client, "_fake_started", False) is False

    # ensure start and stop each called exactly once
    assert start_stop_calls.count("start") == 1
    assert start_stop_calls.count("stop") == 1

    # instance should be removed from cache after stop
    assert key not in core._CLIENT_INSTANCES


@pytest.mark.asyncio
async def test_client_context_manager_ignores_connection_error_during_start(
    monkeypatch, tmp_path
):
    import tg_signer.core as core

    start_calls = 0

    async def fake_start(self):
        del self
        nonlocal start_calls
        start_calls += 1
        raise ConnectionError("temporary network issue")

    monkeypatch.setattr(core.Client, "start", fake_start)

    client = get_client(name="acct", workdir=tmp_path)
    key = client.key

    async with client as current:
        assert current is client
        assert core._CLIENT_REFS[key] == 1

    assert start_calls == 1
    assert key not in core._CLIENT_INSTANCES


@pytest.mark.asyncio
async def test_client_context_manager_ignores_connection_error_during_stop(
    monkeypatch, tmp_path
):
    import tg_signer.core as core

    stop_calls = 0

    async def fake_start(self):
        self._started = True

    async def fake_stop(self):
        del self
        nonlocal stop_calls
        stop_calls += 1
        raise ConnectionError("temporary network issue")

    monkeypatch.setattr(core.Client, "start", fake_start)
    monkeypatch.setattr(core.Client, "stop", fake_stop)

    client = get_client(name="acct", workdir=tmp_path)
    key = client.key

    async with client:
        assert core._CLIENT_REFS[key] == 1

    assert stop_calls == 1
    assert key not in core._CLIENT_INSTANCES


@pytest.mark.asyncio
async def test_login_bootstrap_is_shared_between_concurrent_workers(
    monkeypatch, signer_factory
):
    """Concurrent workers with the same account should only perform one
    get_me/get_dialogs login bootstrap.
    """
    import tg_signer.core as core

    calls = {"get_me": 0, "get_dialogs": 0, "save_session_string": 0}

    async def fake_get_me(self):
        calls["get_me"] += 1
        await asyncio.sleep(0)
        return SimpleNamespace(id=123456)

    async def fake_get_dialogs(self, limit):
        del limit
        calls["get_dialogs"] += 1
        chat = SimpleNamespace(
            id=10001,
            title="test-chat",
            type="private",
            username=None,
            first_name="test",
            last_name=None,
        )
        yield SimpleNamespace(chat=chat)

    async def fake_save_session_string(self):
        calls["save_session_string"] += 1
        await asyncio.sleep(0)

    patch_client_methods(
        monkeypatch,
        core,
        get_me=fake_get_me,
        get_dialogs=fake_get_dialogs,
        save_session_string=fake_save_session_string,
    )

    signer1 = signer_factory(task_name="task_a")
    signer2 = signer_factory(
        task_name="task_b",
    )

    await asyncio.gather(
        signer1.login(num_of_dialogs=20, print_chat=False),
        signer2.login(num_of_dialogs=20, print_chat=False),
    )

    assert calls["get_me"] == 1
    assert calls["get_dialogs"] == 1
    assert calls["save_session_string"] == 1
    assert signer1.user.id == signer2.user.id == 123456


def test_user_signer_load_sign_record_migrates_legacy_json(signer_factory):
    signer = signer_factory(task_name="linuxdo")
    signer.user = SimpleNamespace(id=123456)
    legacy_record_file = signer.task_dir / "sign_record.json"
    legacy_record_file.write_text(
        json.dumps({"2026-03-17": "2026-03-17T06:00:00+08:00"}),
        encoding="utf-8",
    )

    records = signer.load_sign_record()

    assert records == {"2026-03-17": "2026-03-17T06:00:00+08:00"}
    assert signer.sign_record_store.load_records("linuxdo", "123456") == records


def test_user_signer_load_sign_record_logs_migration_hint(monkeypatch, signer_factory):
    signer = signer_factory(task_name="linuxdo")
    signer.user = SimpleNamespace(id=123456)
    legacy_record_file = signer.task_dir / "sign_record.json"
    legacy_record_file.write_text(
        json.dumps({"2026-03-17": "2026-03-17T06:00:00+08:00"}),
        encoding="utf-8",
    )
    messages = []

    def fake_log(message, level="INFO", **kwargs):
        del kwargs
        messages.append((level, message))

    monkeypatch.setattr(signer, "log", fake_log)

    signer.load_sign_record()

    assert any(
        level == "WARNING" and "migrate-sign-records" in message
        for level, message in messages
    )


def test_user_signer_persist_sign_record_writes_sqlite_only_by_default(signer_factory):
    signer = signer_factory(task_name="linuxdo")
    signer.user = SimpleNamespace(id=123456)
    sign_record = {}

    signer.persist_sign_record(
        sign_record,
        "2026-03-17",
        "2026-03-17T06:00:00+08:00",
    )

    assert sign_record == {"2026-03-17": "2026-03-17T06:00:00+08:00"}
    assert signer.sign_record_store.load_records("linuxdo", "123456") == sign_record
    assert not signer.sign_record_file.exists()


@pytest.mark.asyncio
async def test_login_skips_topics_for_non_forum_supergroup(monkeypatch, signer_factory):
    import tg_signer.core as core

    chat = SimpleNamespace(
        id=-1001,
        title="plain-supergroup",
        type=core.ChatType.SUPERGROUP,
        username=None,
        first_name=None,
        last_name=None,
        is_forum=False,
    )
    outputs = setup_login_test(monkeypatch, core, [chat])

    signer = signer_factory()
    signer.get_forum_topics = AsyncMock(return_value=[])

    await signer.login(num_of_dialogs=20, print_chat=True)

    signer.get_forum_topics.assert_not_awaited()
    assert any("plain-supergroup" in str(message) for message in outputs)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("chat_type", "is_forum"),
    [
        pytest.param(ChatType.SUPERGROUP, True, id="legacy-forum-supergroup"),
        pytest.param(ChatType.FORUM, False, id="forum"),
    ],
)
async def test_login_prints_topics_for_forum_chat(
    monkeypatch, signer_factory, chat_type, is_forum
):
    import tg_signer.core as core

    chat = SimpleNamespace(
        id=-1002,
        title=f"{chat_type.name.lower()}-chat",
        type=chat_type,
        username=None,
        first_name=None,
        last_name=None,
        is_forum=is_forum,
    )
    outputs = setup_login_test(monkeypatch, core, [chat])

    signer = signer_factory()
    signer.get_forum_topics = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=1,
                title="General",
                is_closed=False,
                is_pinned=False,
            )
        ]
    )

    await signer.login(num_of_dialogs=20, print_chat=True)

    signer.get_forum_topics.assert_awaited_once_with(chat.id, limit=20)
    assert any("message_thread_id: 1" in str(message) for message in outputs)


@pytest.mark.asyncio
async def test_login_skips_topics_for_direct_chat(monkeypatch, signer_factory):
    import tg_signer.core as core

    chat = SimpleNamespace(
        id=-1004,
        title="direct-chat",
        type=ChatType.DIRECT,
        username=None,
        first_name=None,
        last_name=None,
        is_forum=False,
    )
    outputs = setup_login_test(monkeypatch, core, [chat])

    signer = signer_factory()
    signer.get_forum_topics = AsyncMock(return_value=[])

    await signer.login(num_of_dialogs=20, print_chat=True)

    signer.get_forum_topics.assert_not_awaited()
    assert any("type: 频道私信" in str(message) for message in outputs)


@pytest.mark.asyncio
async def test_login_loads_forum_topics_after_dialog_fetch(monkeypatch, signer_factory):
    import tg_signer.core as core

    async def fake_get_dialogs(self, limit):
        del limit
        yield SimpleNamespace(
            chat=SimpleNamespace(
                id=-1005,
                title="forum-chat",
                type=core.ChatType.FORUM,
                username=None,
                first_name=None,
                last_name=None,
                is_forum=False,
            )
        )

    async def fake_get_forum_topics(self, chat_id, limit=20):
        del chat_id, limit
        yield SimpleNamespace(
            id=1,
            title="General",
            is_closed=False,
            is_pinned=False,
        )

    active_operation = None

    async def guarded_call(self, operation, call, **kwargs):
        del kwargs
        nonlocal active_operation
        assert active_operation is None, (
            f"nested api call detected: {active_operation} -> {operation}"
        )
        active_operation = operation
        try:
            return await call()
        finally:
            active_operation = None

    outputs = collect_outputs(monkeypatch, core)

    patch_client_methods(monkeypatch, core, get_dialogs=fake_get_dialogs)
    monkeypatch.setattr(core.Client, "get_forum_topics", fake_get_forum_topics)
    monkeypatch.setattr(core.BaseUserWorker, "_call_telegram_api", guarded_call)

    signer = signer_factory()

    await signer.login(num_of_dialogs=20, print_chat=True)

    assert any("message_thread_id: 1" in str(message) for message in outputs)


@pytest.mark.asyncio
async def test_client_get_forum_topics_handles_missing_top_message(
    monkeypatch, signer_factory
):
    import tg_signer._kurigram.methods as kurigram_methods
    import tg_signer.core as core

    signer = signer_factory()
    invoke_calls = []

    async def direct_call(_api_name, func):
        return await func()

    async def fake_resolve_peer(chat_id):
        return chat_id

    async def fake_invoke(query):
        invoke_calls.append(query)
        return SimpleNamespace(
            users=[],
            chats=[],
            messages=[SimpleNamespace(id=10)],
            topics=["topic-1", "topic-1-duplicate", "topic-2"],
        )

    async def fake_parse_message(_client, message, _users, _chats):
        return SimpleNamespace(
            id=message.id,
            date=datetime(2026, 3, 8, tzinfo=timezone.utc),
        )

    def fake_parse_topic(_client, topic, messages, _users, _chats):
        if topic == "topic-1":
            return SimpleNamespace(id=1, title="A", top_message=messages[10])
        if topic == "topic-1-duplicate":
            return SimpleNamespace(id=1, title="A duplicate", top_message=messages[10])
        if topic == "topic-2":
            return SimpleNamespace(id=2, title="B", top_message=None)
        return None

    monkeypatch.setattr(signer, "_call_telegram_api", direct_call)
    monkeypatch.setattr(signer.app, "resolve_peer", fake_resolve_peer)
    monkeypatch.setattr(signer.app, "invoke", fake_invoke)
    monkeypatch.setattr(kurigram_methods.types.Message, "_parse", fake_parse_message)
    monkeypatch.setattr(kurigram_methods.types.ForumTopic, "_parse", fake_parse_topic)

    topics = await signer.get_forum_topics(-100123, limit=20)

    assert isinstance(signer.app, core.Client)
    assert [topic.id for topic in topics] == [1, 2]
    assert len(invoke_calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("error_kind", ["timeout", "rpc"])
async def test_login_ignores_topic_lookup_failures(
    monkeypatch, signer_factory, error_kind
):
    import tg_signer.core as core

    chat = SimpleNamespace(
        id=-1003,
        title="forum-supergroup",
        type=core.ChatType.SUPERGROUP,
        username=None,
        first_name=None,
        last_name=None,
        is_forum=True,
    )
    outputs = setup_login_test(monkeypatch, core, [chat])

    signer = signer_factory()
    if error_kind == "timeout":
        error = asyncio.TimeoutError()
    else:
        error = core.errors.RPCError("boom")
    signer.get_forum_topics = AsyncMock(side_effect=error)

    await signer.login(num_of_dialogs=20, print_chat=True)

    signer.get_forum_topics.assert_awaited_once_with(chat.id, limit=20)
    assert signer.user.id == 123456
    assert not any("message_thread_id:" in str(message) for message in outputs)


@pytest.mark.asyncio
async def test_call_telegram_api_retries_floodwait(monkeypatch, signer_factory):
    import tg_signer.core as core

    monkeypatch.setattr(core, "_API_MIN_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(core, "_API_FLOODWAIT_PADDING_SECONDS", 0.0)
    monkeypatch.setattr(core, "_API_MAX_FLOODWAIT_RETRIES", 2)

    waits = []
    real_sleep = core.asyncio.sleep

    async def fake_sleep(seconds):
        waits.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(core.asyncio, "sleep", fake_sleep)

    signer = signer_factory()

    called = 0

    async def flaky_api():
        nonlocal called
        called += 1
        if called == 1:
            raise core.errors.FloodWait(2)
        return "ok"

    result = await signer._call_telegram_api("test", flaky_api)

    assert result == "ok"
    assert called == 2
    assert waits == [2]


@pytest.mark.asyncio
async def test_call_telegram_api_raises_after_max_floodwait_retries(
    monkeypatch, signer_factory
):
    import tg_signer.core as core

    monkeypatch.setattr(core, "_API_MIN_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(core, "_API_FLOODWAIT_PADDING_SECONDS", 0.0)
    monkeypatch.setattr(core, "_API_MAX_FLOODWAIT_RETRIES", 1)

    waits = []
    real_sleep = core.asyncio.sleep

    async def fake_sleep(seconds):
        waits.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(core.asyncio, "sleep", fake_sleep)

    signer = signer_factory()
    called = 0

    async def always_floodwait():
        nonlocal called
        called += 1
        raise core.errors.FloodWait(2)

    with pytest.raises(core.errors.FloodWait):
        await signer._call_telegram_api("test", always_floodwait)

    assert called == 2
    assert waits == [2]
    assert signer.app.key in core._API_LAST_CALL_AT


@pytest.mark.asyncio
async def test_call_telegram_api_without_floodwait_retry_raises_immediately(
    monkeypatch, signer_factory
):
    import tg_signer.core as core

    monkeypatch.setattr(core, "_API_MIN_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(core, "_API_FLOODWAIT_PADDING_SECONDS", 0.0)

    waits = []
    real_sleep = core.asyncio.sleep

    async def fake_sleep(seconds):
        waits.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(core.asyncio, "sleep", fake_sleep)

    signer = signer_factory()

    async def floodwait_once():
        raise core.errors.FloodWait(3)

    with pytest.raises(core.errors.FloodWait):
        await signer._call_telegram_api(
            "test",
            floodwait_once,
            retry_on_floodwait=False,
        )

    assert waits == []
    assert signer.app.key in core._API_LAST_CALL_AT


@pytest.mark.asyncio
async def test_call_telegram_api_is_serialized_for_same_account(
    monkeypatch, signer_factory
):
    import tg_signer.core as core

    monkeypatch.setattr(core, "_API_MIN_INTERVAL_SECONDS", 0.0)

    signer1 = signer_factory(task_name="task_a")
    signer2 = signer_factory(task_name="task_b")

    active = 0
    max_active = 0

    async def critical_api():
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0)
        active -= 1
        return "done"

    await asyncio.gather(
        signer1._call_telegram_api("critical", critical_api),
        signer2._call_telegram_api("critical", critical_api),
    )

    assert max_active == 1


@pytest.mark.asyncio
async def test_wait_for_send_text_passes_message_thread_id(signer_factory):
    signer = signer_factory()
    signer.send_message = AsyncMock(return_value=None)
    chat = SignChatV3(
        chat_id=-1003763902761,
        message_thread_id=1,
        delete_after=10,
        actions=[SendTextAction(text="checkin")],
    )

    await signer.wait_for(chat, chat.actions[0])

    signer.send_message.assert_awaited_once_with(
        -1003763902761,
        "checkin",
        10,
        message_thread_id=1,
    )


@pytest.mark.asyncio
async def test_resolve_chat_route_key_supports_username(monkeypatch, signer_factory):
    signer = signer_factory()
    signer.context = signer.ensure_ctx()
    chat = SignChatV3(
        chat_id="@neo",
        actions=[SendTextAction(text="checkin")],
    )

    async def fake_get_chat(chat_id):
        assert chat_id == "@neo"
        return SimpleNamespace(id=-1003763902761)

    monkeypatch.setattr(signer.app, "get_chat", fake_get_chat)

    route_key = await signer.resolve_chat_route_key(chat)

    assert route_key == (-1003763902761, None)
    assert signer.context.resolved_route_keys[("@neo", None)] == route_key


@pytest.mark.asyncio
async def test_wait_for_uses_resolved_route_key_for_username(signer_factory):
    signer = signer_factory()
    signer.context = signer.ensure_ctx()
    chat = SignChatV3(
        chat_id="@neo",
        actions=[ClickKeyboardByTextAction(text="签到")],
    )
    raw_key = signer.get_route_key("@neo", None)
    resolved_key = signer.get_route_key(-1003763902761, None)
    message = SimpleNamespace(id=99, text="签到", photo=None, reply_markup=None)
    signer.context.resolved_route_keys[raw_key] = resolved_key
    signer.context.chat_messages[resolved_key][99] = message
    signer._click_keyboard_by_text = AsyncMock(return_value=True)

    await signer.wait_for(chat, chat.actions[0], timeout=0.5)

    signer._click_keyboard_by_text.assert_awaited_once_with(chat.actions[0], message)
    assert signer.context.chat_messages[resolved_key][99] is None


@pytest.mark.asyncio
async def test_on_message_routes_by_chat_id_and_message_thread_id(signer_factory):
    signer = signer_factory()
    signer.context = signer.ensure_ctx()
    route_key = signer.get_route_key(-1003763902761, 11)
    signer.context.sign_chats[route_key].append(
        SignChatV3(
            chat_id=-1003763902761,
            message_thread_id=11,
            actions=[SendTextAction(text="checkin")],
        )
    )
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-1003763902761),
        message_thread_id=11,
        id=99,
    )

    await signer._on_message(signer.app, message)

    assert signer.context.chat_messages[route_key][99] is message


@pytest.mark.asyncio
async def test_on_message_falls_back_to_non_thread_route(signer_factory):
    signer = signer_factory()
    signer.context = signer.ensure_ctx()
    fallback_key = signer.get_route_key(-1003763902761, None)
    signer.context.sign_chats[fallback_key].append(
        SignChatV3(
            chat_id=-1003763902761,
            actions=[SendTextAction(text="checkin")],
        )
    )
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-1003763902761),
        message_thread_id=22,
        id=100,
    )

    await signer._on_message(signer.app, message)

    assert signer.context.chat_messages[fallback_key][100] is message


@pytest.mark.asyncio
async def test_on_message_routes_username_chat_by_resolved_chat_id(signer_factory):
    signer = signer_factory()
    signer.context = signer.ensure_ctx()
    resolved_key = signer.get_route_key(-1003763902761, None)
    signer.context.sign_chats[resolved_key].append(
        SignChatV3(
            chat_id="@neo",
            actions=[SendTextAction(text="checkin")],
        )
    )
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-1003763902761),
        message_thread_id=None,
        id=101,
    )

    await signer._on_message(signer.app, message)

    assert signer.context.chat_messages[resolved_key][101] is message


@pytest.mark.asyncio
async def test_on_message_ignores_unexpected_chat(signer_factory):
    signer = signer_factory()
    signer.context = signer.ensure_ctx()
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-1003763902761),
        message_thread_id=22,
        id=100,
    )

    await signer._on_message(signer.app, message)

    assert signer.context.chat_messages == {}


@pytest.mark.asyncio
async def test_schedule_messages_passes_message_thread_id(monkeypatch, signer_factory):
    signer = signer_factory()
    signer.user = SimpleNamespace(id=1)
    calls = []

    class DummyApp:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def send_message(self, chat_id, text, **kwargs):
            calls.append({"chat_id": chat_id, "text": text, "kwargs": dict(kwargs)})
            return True

    async def direct_call(_api_name, func):
        return await func()

    signer.app = DummyApp()
    monkeypatch.setattr(signer, "_call_telegram_api", direct_call)

    await signer.schedule_messages(
        -1003763902761,
        "checkin",
        "0 6 * * *",
        next_times=1,
        random_seconds=0,
        message_thread_id=1,
    )

    assert calls[0]["kwargs"]["message_thread_id"] == 1


@pytest.mark.asyncio
async def test_get_schedule_messages_calls_chat_level_api(monkeypatch, signer_factory):
    signer = signer_factory()
    signer.user = SimpleNamespace(id=1)
    calls = []

    class DummyApp:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get_scheduled_messages(self, chat_id, **kwargs):
            calls.append({"chat_id": chat_id, "kwargs": dict(kwargs)})
            return []

    async def direct_call(_api_name, func):
        return await func()

    signer.app = DummyApp()
    monkeypatch.setattr(signer, "_call_telegram_api", direct_call)

    await signer.get_schedule_messages(-1003763902761)

    assert calls[0]["kwargs"] == {}


def test_normal_run_skips_username_resolution_errors_per_chat(signer_factory):
    import tg_signer.core as core

    signer = signer_factory()
    signer.user = SimpleNamespace(id=1)
    signer.context = signer.ensure_ctx()
    signer._validate_sign_at = lambda *_: "0 0 * * *"
    signer.load_sign_record = lambda: {}
    signer.persist_sign_record = lambda *_args, **_kwargs: None

    config = SignConfigV3(
        chats=[
            SignChatV3(chat_id="@bad", actions=[SendTextAction(text="bad")]),
            SignChatV3(chat_id=123456, actions=[SendTextAction(text="good")]),
        ],
        sign_at="0 0 * * *",
        sign_interval=0,
    )
    signer.load_config = lambda _cls: config

    signed_chats = []

    async def fake_sign_a_chat(chat):
        signed_chats.append(chat.chat_id)

    signer.sign_a_chat = fake_sign_a_chat

    class DummyApp:
        key = "dummy-app"

        def add_handler(self, *_args, **_kwargs):
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get_chat(self, chat_id):
            raise core.errors.UsernameNotOccupied(chat_id)

    signer.app = DummyApp()

    asyncio.run(signer.normal_run(only_once=True))

    assert signed_chats == [123456]
