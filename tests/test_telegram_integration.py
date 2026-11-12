"""Run supported Telegram flows with only Session network calls replaced."""

import asyncio
import json
from collections import Counter
from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from click.testing import CliRunner
from pyrogram import filters, raw
from pyrogram.handlers import EditedMessageHandler, MessageHandler
from pyrogram.types import Chat, ChatMember, ForumTopic, Message, User

from tg_signer.ai_tools import AITools
from tg_signer.automation.engine import UserAutomation
from tg_signer.automation.handlers import register_builtin_handlers
from tg_signer.cli import tg_signer
from tg_signer.config import (
    AutomationConfig,
    ChooseOptionByImageAction,
    ClickKeyboardByTextAction,
    HandlerConfig,
    MatchConfig,
    MessageTriggerConfig,
    MonitorConfig,
    ReplyByCalculationProblemAction,
    RuleConfig,
    SendTextAction,
    SignChatV3,
    SignConfigV3,
)
from tg_signer.core import UserMonitor, UserSigner


@pytest.fixture
def worker(signer_factory, telegram_server):
    return signer_factory(session_string=telegram_server.session_string)


def test_app_run_reuses_loop_for_concurrent_api_calls(worker, telegram_server):
    loops = []
    telegram_server.responses[raw.functions.messages.SendMessage] = lambda query: (
        telegram_server.updates(telegram_server.message(text=query.message))
    )

    async def send_batch():
        loops.append(asyncio.get_running_loop())
        async with worker.app:
            messages = await asyncio.gather(
                worker.send_message(-1000000000005, "first"),
                worker.send_message(-1000000000005, "second"),
                worker.send_message(-1000000000005, "third"),
            )
            assert [message.text for message in messages] == [
                "first",
                "second",
                "third",
            ]

    worker.app_run(send_batch())
    worker.app_run(send_batch())

    assert loops[0] is loops[1] is worker.loop
    assert worker.app._loop is worker.loop
    assert not worker.loop.is_closed()
    assert telegram_server.started == telegram_server.stopped


@pytest.mark.parametrize(
    "args",
    [
        ["login", "-n", "1"],
        ["send-text", "--message-thread-id", "7", "@test_forum", "hello"],
        ["send-dice", "--message-thread-id", "7", "@test_forum", "🎲"],
        ["list-topics", "--chat_id", "@test_forum"],
        ["run-once", "-n", "1", "task"],
        ["logout"],
    ],
)
def test_cli_commands_use_real_client(worker, telegram_server, args):
    worker.write_config(
        SignConfigV3(
            chats=[
                SignChatV3(
                    chat_id=-1000000000005,
                    actions=[SendTextAction(text="checkin")],
                    action_interval=0,
                )
            ],
            sign_at="0 0 * * *",
            sign_interval=0,
        )
    )
    telegram_server.responses[raw.functions.messages.SendMessage] = lambda query: (
        telegram_server.updates(telegram_server.message(text=query.message))
    )
    telegram_server.responses[raw.functions.messages.SendMedia] = (
        telegram_server.updates(
            telegram_server.message(
                media=raw.types.MessageMediaDice(value=4, emoticon="🎲")
            )
        )
    )
    telegram_server.responses[raw.functions.auth.LogOut] = raw.types.auth.LoggedOut()
    result = CliRunner().invoke(
        tg_signer,
        [
            "--workdir",
            str(worker.workdir),
            "--session_dir",
            str(worker._session_dir),
            "--account",
            "acct",
            "--session-string",
            telegram_server.session_string,
            "--log-dir",
            str(worker.workdir / "logs"),
            *args,
        ],
        env={"TG_PROXY": None},
    )

    assert result.exit_code == 0, result.exception
    assert telegram_server.started
    assert telegram_server.started == telegram_server.stopped
    assert not worker.app.is_connected


@pytest.mark.asyncio
async def test_login_parses_dialogs_topics_and_saves_session(
    worker, telegram_server, capsys
):
    await worker.login(num_of_dialogs=1)

    assert isinstance(worker.user, User)
    assert worker.user.id == telegram_server.me.id
    output = capsys.readouterr().out
    assert "Test forum" in output
    assert "message_thread_id: 7, title: Check-in" in output
    chats = json.loads(
        (worker.get_user_dir(worker.user) / "latest_chats.json").read_text()
    )
    assert chats[0]["id"] == -1000000000005
    assert worker.app.session_string_file.read_text() == telegram_server.session_string
    assert not worker.app.is_connected
    assert not worker.app.is_initialized
    assert telegram_server.started == telegram_server.stopped


@pytest.mark.asyncio
async def test_send_reply_delete_dice_and_callback(worker, telegram_server):
    await worker.login(num_of_dialogs=1, print_chat=False)
    telegram_server.responses[raw.functions.messages.SendMessage] = lambda query: (
        telegram_server.updates(
            telegram_server.message(
                text=query.message,
                reply_to=raw.types.MessageReplyHeader(
                    forum_topic=True, reply_to_top_id=7, reply_to_msg_id=7
                ),
            )
        )
    )
    telegram_server.responses[raw.functions.channels.DeleteMessages] = (
        raw.types.messages.AffectedMessages(pts=1, pts_count=1)
    )
    telegram_server.responses[raw.functions.messages.SendMedia] = lambda query: (
        telegram_server.updates(
            telegram_server.message(
                media=raw.types.MessageMediaDice(value=4, emoticon="🎲")
            )
        )
    )
    telegram_server.responses[raw.functions.messages.GetBotCallbackAnswer] = (
        raw.types.messages.BotCallbackAnswer(cache_time=0, message="Checked in")
    )

    async with worker.app:
        message = await worker.send_message(
            -1000000000005,
            "hello",
            delete_after=0,
            message_thread_id=7,
            reply_to_message_id=10,
        )
        assert isinstance(message, Message)
        assert isinstance(message.chat, Chat)
        assert message.text == "hello"
        assert message.message_thread_id == 7
        dice = await worker.send_dice(-1000000000005, message_thread_id=7)
        assert isinstance(dice, Message)
        assert dice.dice.value == 4
        await worker.request_callback_answer(worker.app, -1000000000005, 10, "checkin")

    sent = next(
        q
        for q in telegram_server.queries
        if isinstance(q, raw.functions.messages.SendMessage)
    )
    assert sent.reply_to.top_msg_id == 7
    assert sent.reply_to.reply_to_msg_id == 10
    callback = next(
        q
        for q in telegram_server.queries
        if isinstance(q, raw.functions.messages.GetBotCallbackAnswer)
    )
    assert callback.data == b"checkin"
    assert any(
        isinstance(q, raw.functions.channels.DeleteMessages)
        for q in telegram_server.queries
    )


@pytest.mark.asyncio
async def test_folder_and_topic_queries(worker, telegram_server, capsys):
    peer = raw.types.InputPeerChannel(channel_id=5, access_hash=43)
    telegram_server.responses[raw.functions.messages.GetDialogFilters] = (
        raw.types.messages.DialogFilters(
            filters=[
                raw.types.DialogFilter(
                    id=7,
                    title=raw.types.TextWithEntities(text="Sign", entities=[]),
                    pinned_peers=[peer],
                    include_peers=[peer],
                    exclude_peers=[],
                )
            ]
        )
    )
    telegram_server.responses[raw.functions.messages.GetPeerDialogs] = (
        raw.types.messages.PeerDialogs(
            dialogs=[],
            messages=[],
            users=[telegram_server.me],
            chats=[telegram_server.channel],
            state=raw.types.updates.State(pts=1, qts=0, date=0, seq=1, unread_count=0),
        )
    )
    await worker.login(folder="Sign")
    await worker.list_folders()
    topics = await worker.list_topics(-1000000000005)

    assert isinstance(topics[0], ForumTopic)
    assert topics[0].name == "Check-in"
    assert "name: Sign" in capsys.readouterr().out
    assert not any(
        isinstance(q, raw.functions.messages.GetDialogs)
        for q in telegram_server.queries
    )


@pytest.mark.asyncio
async def test_scheduled_messages(worker, telegram_server, capsys):
    await worker.login(num_of_dialogs=1, print_chat=False)
    telegram_server.responses[raw.functions.messages.SendMessage] = lambda query: (
        telegram_server.updates(
            telegram_server.message(text=query.message), scheduled=True
        )
    )
    telegram_server.responses[raw.functions.messages.GetScheduledHistory] = (
        raw.types.messages.Messages(
            messages=[telegram_server.message(text="scheduled")],
            topics=[],
            chats=[telegram_server.channel],
            users=[telegram_server.me],
        )
    )

    await worker.schedule_messages(
        -1000000000005,
        "scheduled",
        "0 6 * * *",
        next_times=1,
        random_seconds=0,
        message_thread_id=7,
    )
    await worker.get_schedule_messages(-1000000000005)

    sent = next(
        q
        for q in telegram_server.queries
        if isinstance(q, raw.functions.messages.SendMessage)
    )
    assert sent.schedule_date > 0
    assert sent.reply_to.reply_to_msg_id == 7
    assert "scheduled" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_members_are_parsed_users(worker, telegram_server, capsys):
    telegram_server.responses[raw.functions.channels.GetParticipants] = (
        raw.types.channels.ChannelParticipants(
            count=1,
            participants=[raw.types.ChannelParticipant(user_id=123456, date=0)],
            users=[telegram_server.me],
            chats=[telegram_server.channel],
        )
    )
    await worker.login(num_of_dialogs=1, print_chat=False)
    async with worker.app:
        members = [
            member
            async for member in worker.search_members(-1000000000005, query="", limit=1)
        ]
        assert isinstance(members[0], ChatMember)
        assert isinstance(members[0].user, User)
        await worker.list_members(-1000000000005, limit=1)
    assert "Test" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_logout_stops_client_and_deletes_session(worker, telegram_server):
    telegram_server.responses[raw.functions.auth.LogOut] = raw.types.auth.LoggedOut()
    worker.app.session_string_file.write_text(telegram_server.session_string)

    assert await worker.logout()

    assert telegram_server.started == telegram_server.stopped
    assert not worker.app.is_connected
    assert not worker.app.is_initialized
    assert not worker.app.session_string_file.exists()


@pytest.mark.asyncio
async def test_captcha_actions_use_parsed_keyboard_and_download(
    worker, telegram_server, monkeypatch
):
    await worker.login(num_of_dialogs=1, print_chat=False)
    photo = raw.types.Photo(
        id=1,
        access_hash=2,
        file_reference=b"test",
        date=0,
        dc_id=2,
        sizes=[raw.types.PhotoSize(type="x", w=320, h=240, size=5)],
    )
    message = telegram_server.message(
        text="Choose the item",
        media=raw.types.MessageMediaPhoto(photo=photo),
        reply_markup=raw.types.ReplyInlineMarkup(
            rows=[
                raw.types.KeyboardInlineButtonRow(
                    buttons=[
                        raw.types.KeyboardInlineButton(
                            text="Phone",
                            type=raw.types.InlineButtonTypeCallback(data=b"phone"),
                        ),
                        raw.types.KeyboardInlineButton(
                            text="TV",
                            type=raw.types.InlineButtonTypeCallback(data=b"tv"),
                        ),
                    ],
                )
            ]
        ),
    )
    telegram_server.responses[raw.functions.messages.GetHistory] = (
        raw.types.messages.Messages(
            messages=[message],
            topics=[],
            chats=[telegram_server.channel],
            users=[telegram_server.me],
        )
    )
    telegram_server.responses[raw.functions.help.GetConfig] = raw.types.Config(
        date=0,
        expires=2147483647,
        test_mode=False,
        this_dc=2,
        dc_options=[raw.types.DcOption(id=2, ip_address="149.154.167.51", port=443)],
        dc_txt_domain_name="localhost",
        chat_size_max=200,
        megagroup_size_max=200000,
        forwarded_count_max=100,
        online_update_period_ms=1000,
        offline_blur_timeout_ms=1000,
        offline_idle_timeout_ms=1000,
        online_cloud_timeout_ms=1000,
        notify_cloud_delay_ms=1000,
        notify_default_delay_ms=1000,
        push_chat_period_ms=1000,
        push_chat_limit=100,
        edit_time_limit=100,
        revoke_time_limit=100,
        revoke_pm_time_limit=100,
        rating_e_decay=100,
        stickers_recent_limit=100,
        channels_read_media_period=100,
        call_receive_timeout_ms=1000,
        call_ring_timeout_ms=1000,
        call_connect_timeout_ms=1000,
        call_packet_timeout_ms=1000,
        me_url_prefix="https://t.me/",
        caption_length_max=1024,
        message_length_max=4096,
        webfile_dc_id=2,
    )
    telegram_server.responses[raw.functions.upload.GetFile] = raw.types.upload.File(
        type=raw.types.storage.FileJpeg(), mtime=0, bytes=b"image"
    )
    telegram_server.responses[raw.functions.messages.GetBotCallbackAnswer] = (
        raw.types.messages.BotCallbackAnswer(cache_time=0)
    )
    ai_tools = Mock(spec=AITools)
    ai_tools.choose_option_by_image = AsyncMock(return_value=1)
    ai_tools.calculate_problem = AsyncMock(return_value="TV")
    monkeypatch.setattr(worker, "get_ai_tools", lambda: ai_tools)

    async with worker.app:
        parsed = [
            message
            async for message in worker.app.get_chat_history(-1000000000005, limit=1)
        ]
        assert isinstance(parsed[0], Message)
        assert parsed[0].photo.width == 320
        assert await worker._choose_option_by_image(
            ChooseOptionByImageAction(), parsed[0]
        )
        assert await worker._click_keyboard_by_text(
            ClickKeyboardByTextAction(text="TV"), parsed[0]
        )
        assert await worker._reply_by_calculation_problem(
            ReplyByCalculationProblemAction(), parsed[0]
        )

    ai_tools.choose_option_by_image.assert_awaited_once_with(
        b"image", "Choose the item", [(0, "Phone"), (1, "TV")]
    )
    callback = next(
        q
        for q in telegram_server.queries
        if isinstance(q, raw.functions.messages.GetBotCallbackAnswer)
    )
    assert callback.data == b"tv"
    assert Counter(telegram_server.started) == Counter(telegram_server.stopped)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("worker_cls", "edited"),
    [
        (UserSigner, False),
        (UserSigner, True),
        (UserMonitor, False),
        (UserAutomation, False),
        (UserAutomation, True),
    ],
)
async def test_raw_updates_reach_worker_handlers(
    signer_factory, telegram_server, worker_cls, edited
):
    worker = signer_factory(
        cls=worker_cls, session_string=telegram_server.session_string
    )
    chat_id = -1000000000005
    if worker_cls is UserSigner:
        route = worker.get_route_key(chat_id, 7)
        worker.context.sign_chats[route].append(
            SignChatV3(
                chat_id=chat_id,
                message_thread_id=7,
                actions=[SendTextAction(text="ok")],
            )
        )
    elif worker_cls is UserMonitor:
        worker.config = MonitorConfig(
            match_cfgs=[
                MatchConfig(
                    chat_id=chat_id,
                    rule="contains",
                    rule_value="hello",
                    default_send_text="reply",
                )
            ]
        )
    else:
        register_builtin_handlers()
        worker.config = AutomationConfig(
            rules=[
                RuleConfig(
                    id="reply",
                    triggers=[
                        MessageTriggerConfig(
                            type="message", params={"chat_id": chat_id}
                        )
                    ],
                    handlers=[
                        HandlerConfig(handler="reply_text", params={"text": "reply"}),
                        HandlerConfig(handler="forward", params={"chat_id": chat_id}),
                    ],
                )
            ]
        )
    await worker.login(num_of_dialogs=1, print_chat=False)
    telegram_server.responses[raw.functions.messages.SendMessage] = lambda query: (
        telegram_server.updates(telegram_server.message(text=query.message))
    )
    telegram_server.responses[raw.functions.messages.ForwardMessages] = (
        telegram_server.updates(telegram_server.message())
    )
    done = asyncio.Event()
    seen = []

    async def observed(client, message):
        seen.append(message)
        done.set()

    handler = EditedMessageHandler if edited else MessageHandler
    callback = worker.on_edited_message if edited else worker.on_message
    worker.app.add_handler(handler(callback, filters.chat(chat_id)))
    worker.app.add_handler(handler(observed), group=1)
    message = telegram_server.message(
        reply_to=raw.types.MessageReplyHeader(
            forum_topic=True, reply_to_msg_id=7, reply_to_top_id=7
        )
    )
    update_type = (
        raw.types.UpdateEditChannelMessage
        if edited
        else raw.types.UpdateNewChannelMessage
    )
    update = update_type(message=message, pts=1, pts_count=1)
    update = raw.core.TLObject.read(BytesIO(update.write()))

    async with worker.app:
        worker.app.dispatcher.enqueue(
            update,
            users={telegram_server.me.id: telegram_server.me},
            chats={
                telegram_server.channel.id: raw.core.TLObject.read(
                    BytesIO(telegram_server.channel.write())
                )
            },
        )
        await asyncio.wait_for(done.wait(), timeout=3)

    assert isinstance(seen[0], Message)
    assert isinstance(seen[0].from_user, User)
    assert seen[0].message_thread_id == 7
    if worker_cls is UserSigner:
        assert worker.context.chat_messages[route][10] is seen[0]
    else:
        assert any(
            isinstance(query, raw.functions.messages.SendMessage)
            and query.message == "reply"
            for query in telegram_server.queries
        )
        if worker_cls is UserAutomation:
            assert any(
                isinstance(query, raw.functions.messages.ForwardMessages)
                and query.id == [10]
                for query in telegram_server.queries
            )
    assert not worker.app.dispatcher.handler_worker_tasks
