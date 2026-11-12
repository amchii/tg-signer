import asyncio
import contextlib
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from pyrogram.enums import ChatType
from pyrogram.types import Chat, Message, User

from tg_signer.automation.engine import UserAutomation
from tg_signer.automation.handlers import register_builtin_handlers
from tg_signer.config import (
    AutomationConfig,
    FilterConfig,
    HandlerConfig,
    MessageTriggerConfig,
    RuleConfig,
    TimerTriggerConfig,
)


def make_worker(tmp_path):
    return UserAutomation(
        task_name="t",
        account="test_account",
        workdir=tmp_path,
        session_dir=tmp_path,
    )


def test_match_filter_variants(tmp_path):
    worker = make_worker(tmp_path)
    chat = Chat(type=ChatType.GROUP, id=1, username="room")
    user = User(id=2, username="Neo", is_self=False)
    msg = Message(id=1, text="Hello World", chat=chat, from_user=user)

    assert worker._match_filter(
        FilterConfig(text_rule="contains", text_value="world", ignore_case=True),
        msg,
    )
    assert worker._match_filter(
        FilterConfig(text_rule="exact", text_value="Hello World", ignore_case=True),
        msg,
    )
    assert not worker._match_filter(
        FilterConfig(text_rule="exact", text_value="hello", ignore_case=False),
        msg,
    )
    assert worker._match_filter(
        FilterConfig(text_rule="regex", text_value=r"Hello\s+World"),
        msg,
    )
    assert worker._match_filter(FilterConfig(text_rule="all"), msg)
    assert not worker._match_filter(
        FilterConfig(text_rule="contains", text_value=""), msg
    )


def test_match_message_trigger_and_user(tmp_path):
    worker = make_worker(tmp_path)
    chat = Chat(type=ChatType.GROUP, id=1, username="room")
    me = User(id=99, username="me", is_self=True)
    other = User(id=2, username="neo", is_self=False)
    replied = Message(id=1, text="hi", chat=chat, from_user=me)
    msg = Message(id=1, text="ok", chat=chat, from_user=other, reply_to_message=replied)

    trigger = MessageTriggerConfig(
        type="message", params={"chat_id": 1, "reply_to_me": True}
    )
    assert worker._match_message_trigger(trigger, msg)

    trigger = MessageTriggerConfig(type="message", params={"from_user_ids": ["neo", 2]})
    assert worker._match_message_trigger(trigger, msg)

    trigger = MessageTriggerConfig(type="message", params={"from_user_ids": ["me"]})
    assert not worker._match_message_trigger(trigger, msg)


def test_match_chat_ids_and_username(tmp_path):
    worker = make_worker(tmp_path)
    chat = Chat(type=ChatType.GROUP, id=1, username="room")
    msg = Message(id=1, text="ok", chat=chat)

    assert worker._match_chat(msg, 1, None)
    assert worker._match_chat(msg, "@room", None)
    assert worker._match_chat(msg, None, ["@room", 2])
    assert not worker._match_chat(msg, None, ["@other"])


def test_compute_next_run_interval_and_cron(tmp_path):
    worker = make_worker(tmp_path)
    now = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)

    trigger = TimerTriggerConfig(type="timer", params={"interval_seconds": 60})
    assert worker._compute_next_run(trigger, now) == now + timedelta(seconds=60)

    trigger = TimerTriggerConfig(type="timer", params={"cron": "*/5 * * * *"})
    next_dt = worker._compute_next_run(trigger, now)
    assert next_dt is not None
    assert next_dt > now


@pytest.mark.asyncio
async def test_timer_schedule_next_override(tmp_path, monkeypatch):
    """验证 timer 触发后 schedule_next 能覆盖默认间隔计算。"""
    worker = make_worker(tmp_path)
    register_builtin_handlers()

    now = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    cfg = AutomationConfig(
        rules=[
            RuleConfig(
                id="r1",
                enabled=True,
                triggers=[
                    TimerTriggerConfig(
                        id="timer1",
                        type="timer",
                        params={"interval_seconds": 60},
                    )
                ],
                handlers=[
                    HandlerConfig(
                        handler="schedule_next",
                        params={"delay_seconds": 300},
                    )
                ],
            )
        ]
    )
    worker.config = cfg
    worker.state.set_trigger_next_run("r1", "timer1", now)

    import tg_signer.automation.engine as engine

    # 固定当前时间，避免定时循环受真实时间影响
    monkeypatch.setattr(engine, "get_now", lambda: now)

    # 运行一次 timer_loop 周期后取消，模拟单轮触发
    task = asyncio.create_task(worker.timer_loop())
    await asyncio.sleep(0.01)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    next_run = worker.state.get_trigger_next_run("r1", "timer1")
    assert next_run == now + timedelta(seconds=300)


@pytest.mark.asyncio
async def test_on_edited_message_matches_message_trigger(tmp_path):
    """编辑消息应复用 message trigger 匹配链路。"""
    worker = make_worker(tmp_path)
    worker.config = AutomationConfig(
        rules=[
            RuleConfig(
                id="r1",
                enabled=True,
                triggers=[MessageTriggerConfig(type="message", params={"chat_id": 1})],
                handlers=[],
            )
        ]
    )
    events: list[tuple[str, str, int]] = []

    async def fake_run_rule(rule, event):
        events.append((rule.id, event.type, event.chat_id))

    worker._run_rule = fake_run_rule  # type: ignore[method-assign]
    msg = Message(
        id=1, text="edited", chat=Chat(type=ChatType.GROUP, id=1, username="room")
    )

    await worker.on_edited_message(None, msg)

    assert events == [("r1", "edited_message", 1)]


@pytest.mark.asyncio
async def test_on_edited_message_updates_cache(tmp_path):
    """编辑消息应覆盖缓存中的同 message_id 内容。"""
    worker = make_worker(tmp_path)
    worker.config = AutomationConfig(rules=[])

    original = Message(
        id=100, text="before", chat=Chat(type=ChatType.GROUP, id=1, username="room")
    )
    edited = Message(
        id=100, text="after", chat=Chat(type=ChatType.GROUP, id=1, username="room")
    )

    await worker.on_message(None, original)
    await worker.on_edited_message(None, edited)

    cached = worker.get_cached_messages(1)
    assert len(cached) == 1
    assert cached[0].text == "after"


def test_trigger_rejects_unknown_params_key():
    """强类型触发器应拒绝未定义字段，避免静默吞掉拼写错误。"""
    with pytest.raises(ValidationError):
        RuleConfig.model_validate(
            {
                "id": "invalid_trigger",
                "triggers": [
                    {
                        "type": "message",
                        "params": {"chat_id": 123, "interval_secondz": 1},
                    }
                ],
                "handlers": [{"handler": "send_text", "params": {"text": "ok"}}],
            }
        )


def test_trigger_rejects_legacy_flatten_fields():
    """只接受 type+params 结构，不再兼容平铺字段。"""
    with pytest.raises(ValidationError):
        RuleConfig.model_validate(
            {
                "id": "legacy_flatten",
                "triggers": [{"type": "message", "chat_id": 123, "reply_to_me": True}],
                "handlers": [{"handler": "send_text", "params": {"text": "ok"}}],
            }
        )
