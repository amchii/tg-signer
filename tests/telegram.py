"""Concrete Telegram objects shared by offline tests."""

import base64
import struct
from datetime import datetime, timezone
from io import BytesIO

from pyrogram import raw
from pyrogram.storage import Storage
from pyrogram.types import Chat, Dialog, Message, Photo


def make_dialog(chat: Chat) -> Dialog:
    return Dialog(
        chat=chat,
        top_message=Message(id=1, chat=chat),
        last_read_inbox_message_id=0,
        last_read_outbox_message_id=0,
        unread_messages_count=0,
        unread_mentions_count=0,
        unread_reactions_count=0,
        unread_poll_vote_count=0,
        unread_mark=False,
        is_pinned=False,
    )


def make_photo(file_id: str) -> Photo:
    return Photo(
        file_id=file_id,
        file_unique_id="test-photo",
        width=320,
        height=240,
        file_size=1024,
        date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_raw_topic(id: int, title: str, top_message: int = 10) -> raw.types.ForumTopic:
    return raw.types.ForumTopic(
        id=id,
        date=0,
        peer=raw.types.PeerChannel(channel_id=5),
        title=title,
        icon_color=0,
        top_message=top_message,
        read_inbox_max_id=0,
        read_outbox_max_id=0,
        unread_count=0,
        unread_mentions_count=0,
        unread_reactions_count=0,
        unread_poll_votes_count=0,
        from_id=raw.types.PeerUser(user_id=123456),
        notify_settings=raw.types.PeerNotifySettings(),
    )


class TelegramServer:
    """Scripted RPC responses at the Session boundary, using real TL objects."""

    def __init__(self):
        self.queries = []
        self.started = []
        self.stopped = []
        self.me = raw.types.User(
            id=123456, access_hash=42, first_name="Test", is_self=True
        )
        self.channel = raw.types.Channel(
            id=5,
            access_hash=43,
            title="Test forum",
            username="test_forum",
            photo=raw.types.ChatPhotoEmpty(),
            date=0,
            megagroup=True,
            forum=True,
        )
        self.responses = {
            raw.functions.contacts.ResolveUsername: raw.types.contacts.ResolvedPeer(
                peer=raw.types.PeerChannel(channel_id=self.channel.id),
                users=[],
                chats=[self.channel],
            ),
            raw.functions.channels.GetChannels: raw.types.messages.Chats(
                chats=[self.channel]
            ),
            raw.functions.channels.GetMessages: raw.types.messages.Messages(
                messages=[self.message()],
                topics=[],
                users=[self.me],
                chats=[self.channel],
            ),
            raw.functions.updates.GetState: raw.types.updates.State(
                pts=1, qts=0, date=0, seq=1, unread_count=0
            ),
            raw.functions.users.GetFullUser: raw.types.users.UserFull(
                full_user=raw.types.UserFull(
                    id=self.me.id,
                    settings=raw.types.PeerSettings(),
                    notify_settings=raw.types.PeerNotifySettings(),
                    common_chats_count=0,
                ),
                users=[self.me],
                chats=[],
            ),
            raw.functions.messages.GetDialogs: raw.types.messages.Dialogs(
                dialogs=[
                    raw.types.Dialog(
                        peer=raw.types.PeerChannel(channel_id=self.channel.id),
                        top_message=10,
                        read_inbox_max_id=0,
                        read_outbox_max_id=0,
                        unread_count=0,
                        unread_mentions_count=0,
                        unread_reactions_count=0,
                        unread_poll_votes_count=0,
                        notify_settings=raw.types.PeerNotifySettings(),
                    )
                ],
                messages=[self.message()],
                chats=[self.channel],
                users=[self.me],
            ),
            raw.functions.messages.GetForumTopics: raw.types.messages.ForumTopics(
                count=1,
                topics=[make_raw_topic(7, "Check-in")],
                messages=[],
                chats=[self.channel],
                users=[self.me],
                pts=1,
            ),
        }
        self.responses[raw.functions.messages.GetForumTopicsByID] = lambda query: (
            raw.types.messages.ForumTopics(
                count=len(query.topics),
                topics=[make_raw_topic(id, "General") for id in query.topics],
                messages=[],
                chats=[self.channel],
                users=[self.me],
                pts=1,
            )
        )
        self.session_string = (
            base64.urlsafe_b64encode(
                struct.pack(
                    Storage.SESSION_STRING_FORMAT,
                    2,
                    12345,
                    False,
                    bytes(256),
                    self.me.id,
                    False,
                )
            )
            .decode()
            .rstrip("=")
        )

    async def invoke(self, query):
        query.write()
        self.queries.append(query)
        if type(query) not in self.responses:
            raise AssertionError(f"Unexpected Telegram RPC: {type(query).__name__}")
        response = self.responses[type(query)]
        if callable(response) and not isinstance(response, raw.core.TLObject):
            response = response(query)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, bool):
            return response
        if not isinstance(response, raw.core.TLObject):
            raise TypeError("Telegram responses must be real TL objects")
        return raw.core.TLObject.read(BytesIO(response.write()))

    def message(self, id=10, text="hello", from_id=None, **kwargs):
        return raw.types.Message(
            id=id,
            peer_id=raw.types.PeerChannel(channel_id=self.channel.id),
            from_id=from_id or raw.types.PeerUser(user_id=self.me.id),
            date=1767225600,
            message=text,
            **kwargs,
        )

    def updates(self, message, scheduled=False):
        update = (
            raw.types.UpdateNewScheduledMessage(message=message)
            if scheduled
            else raw.types.UpdateNewChannelMessage(message=message, pts=1, pts_count=1)
        )
        return raw.types.Updates(
            updates=[update], users=[self.me], chats=[self.channel], date=0, seq=1
        )
