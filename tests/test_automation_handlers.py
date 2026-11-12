import logging
from datetime import datetime, timezone

import pytest
from pyrogram import raw
from pyrogram.types import Message

from tg_signer.automation.handlers import (
    ai_reply,
    blacklist_filter,
    extract_regex,
    load_plugins,
    random_pick,
    schedule_next,
)
from tg_signer.automation.models import AutomationContext, Event, RuleStateStore


class DummyWorker:
    """仅用于验证 handler 调用与参数透传。"""

    def __init__(self):
        self.sent = []
        self.ai_tools = DummyAITools()

    async def send_message(
        self, chat_id, text, delete_after=None, reply_to_message_id=None
    ):
        self.sent.append((chat_id, text, delete_after, reply_to_message_id))

    def get_ai_tools(self):
        return self.ai_tools


class DummyAITools:
    def __init__(self):
        self.calls = []

    async def get_reply(self, prompt, query):
        self.calls.append((prompt, query))
        return "AI-RESP"


@pytest.mark.asyncio
async def test_extract_regex_sets_var(tmp_path):
    """extract_regex 应将捕获结果写入 ctx.vars。"""
    state = RuleStateStore(tmp_path / "state.json", logging.getLogger("test"))
    worker = DummyWorker()
    event = Event(
        type="message",
        chat_id=123,
        message=Message(id=1, text="cooldown 42"),
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
        trigger_id="t1",
        rule_id="r1",
    )
    ctx = AutomationContext(
        vars={},
        state=state,
        client=None,
        logger=logging.getLogger("test"),
        worker=worker,
        workdir=tmp_path,
    )

    await extract_regex(event, ctx, {"pattern": r"cooldown (\d+)", "var": "x"})
    assert ctx.vars["x"] == "42"


@pytest.mark.asyncio
async def test_schedule_next_writes_state(tmp_path):
    """schedule_next 应写入 trigger 的 next_run_at。"""
    state = RuleStateStore(tmp_path / "state.json", logging.getLogger("test"))
    event = Event(
        type="timer",
        chat_id=None,
        message=None,
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
        trigger_id="t1",
        rule_id="r1",
    )
    ctx = AutomationContext(
        vars={},
        state=state,
        client=None,
        logger=logging.getLogger("test"),
        worker=DummyWorker(),
        workdir=tmp_path,
    )

    await schedule_next(event, ctx, {"delay_seconds": 30})
    assert state.get_trigger_next_run("r1", "t1") == datetime(
        2024, 1, 1, 0, 0, 30, tzinfo=timezone.utc
    )


@pytest.mark.asyncio
async def test_schedule_next_from_var_minutes(tmp_path):
    """schedule_next 支持 from_var 按分钟解释。"""
    state = RuleStateStore(tmp_path / "state.json", logging.getLogger("test"))
    event = Event(
        type="timer",
        chat_id=None,
        message=None,
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
        trigger_id="t1",
        rule_id="r1",
    )
    ctx = AutomationContext(
        vars={"cooldown": "5"},
        state=state,
        client=None,
        logger=logging.getLogger("test"),
        worker=DummyWorker(),
        workdir=tmp_path,
    )

    await schedule_next(
        event,
        ctx,
        {
            "from_var": "cooldown",
            "from_var_unit": "minutes",
            "offset_seconds": 30,
        },
    )
    assert state.get_trigger_next_run("r1", "t1") == datetime(
        2024, 1, 1, 0, 5, 30, tzinfo=timezone.utc
    )


@pytest.mark.asyncio
async def test_random_pick_sets_var(tmp_path):
    """random_pick 在指定 var 时不发送消息，仅写变量。"""
    state = RuleStateStore(tmp_path / "state.json", logging.getLogger("test"))
    event = Event(
        type="message",
        chat_id=1,
        message=Message(id=1, text="hi"),
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
        trigger_id="t1",
        rule_id="r1",
    )
    ctx = AutomationContext(
        vars={},
        state=state,
        client=None,
        logger=logging.getLogger("test"),
        worker=DummyWorker(),
        workdir=tmp_path,
    )

    await random_pick(event, ctx, {"choices": ["a", "b"], "var": "pick"})
    assert ctx.vars["pick"] in {"a", "b"}


@pytest.mark.asyncio
async def test_blacklist_filter_source_var(tmp_path):
    """blacklist_filter 可过滤变量中的文本。"""
    state = RuleStateStore(tmp_path / "state.json", logging.getLogger("test"))
    event = Event(
        type="message",
        chat_id=1,
        message=Message(id=1, text="safe text"),
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
        trigger_id="t1",
        rule_id="r1",
    )
    ctx = AutomationContext(
        vars={"ai_text": "This contains BAD word"},
        state=state,
        client=None,
        logger=logging.getLogger("test"),
        worker=DummyWorker(),
        workdir=tmp_path,
    )

    result = await blacklist_filter(
        event,
        ctx,
        {"source_var": "ai_text", "keywords": ["bad"], "ignore_case": True},
    )
    assert result == "stop"


@pytest.mark.asyncio
async def test_ai_reply_uses_recent_messages(
    tmp_path, signer_factory, telegram_server, monkeypatch
):
    """ai_reply 可按 recent_limit 读取历史消息作为输入。"""
    state = RuleStateStore(tmp_path / "state.json", logging.getLogger("test"))
    worker = signer_factory(session_string=telegram_server.session_string)
    ai_tools = DummyAITools()
    monkeypatch.setattr(worker, "get_ai_tools", lambda: ai_tools)
    history = [
        telegram_server.message(
            id=2,
            text="最新消息",
            from_id=raw.types.PeerUser(user_id=1),
        ),
        telegram_server.message(
            id=1,
            text="更早消息",
            from_id=raw.types.PeerUser(user_id=2),
        ),
    ]
    telegram_server.responses[raw.functions.messages.GetHistory] = (
        raw.types.messages.Messages(
            messages=history,
            topics=[],
            chats=[telegram_server.channel],
            users=[
                raw.types.User(id=1, first_name="Neo", username="neo"),
                raw.types.User(id=2, first_name="Trinity", username="trinity"),
            ],
        )
    )
    telegram_server.responses[raw.functions.messages.SendMessage] = lambda query: (
        telegram_server.updates(telegram_server.message(text=query.message))
    )
    await worker.login(num_of_dialogs=1, print_chat=False)
    event = Event(
        type="message",
        chat_id=-1000000000005,
        message=Message(text="当前消息", id=99),
        now=datetime(2024, 1, 1, tzinfo=timezone.utc),
        trigger_id="t1",
        rule_id="r1",
    )
    ctx = AutomationContext(
        vars={},
        state=state,
        client=worker.app,
        logger=logging.getLogger("test"),
        worker=worker,
        workdir=tmp_path,
    )

    async with worker.app:
        result = await ai_reply(
            event,
            ctx,
            {
                "prompt": "你是测试助手",
                "recent_limit": 2,
                "store_var": "ai_text",
            },
        )
    assert result == "continue"
    assert ctx.vars["ai_text"] == "AI-RESP"
    _, query = ai_tools.calls[0]
    assert "[@trinity] 更早消息" in query
    assert "[@neo] 最新消息" in query


def test_load_plugins_registers_handlers(tmp_path):
    """插件加载后应可通过 get_handler 获取到注册函数。"""
    handlers_dir = tmp_path / "handlers"
    handlers_dir.mkdir(parents=True, exist_ok=True)
    plugin_path = handlers_dir / "plugin.py"
    plugin_path.write_text(
        "async def hello(event, ctx, params):\n"
        "    return 'continue'\n\n"
        "HANDLERS = {'plugin_hello': hello}\n",
        encoding="utf-8",
    )

    load_plugins(handlers_dir, logging.getLogger("test"))

    from tg_signer.automation.handlers import get_handler

    assert get_handler("plugin_hello") is not None
