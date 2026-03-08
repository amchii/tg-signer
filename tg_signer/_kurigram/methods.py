from typing import AsyncGenerator, Union

import pyrogram
from pyrogram import raw, types, utils


class SafeGetForumTopics:
    """Temporary workaround for Kurigram forum topic pagination.

    Kurigram 2.2.19 may raise AttributeError when the last topic in a page has
    no ``top_message``. Keep this patch isolated so it can be removed once the
    upstream method is fixed.
    """

    async def get_forum_topics(
        self: "pyrogram.Client",
        chat_id: Union[int, str],
        limit: int = 0,
    ) -> AsyncGenerator["types.ForumTopic", None]:
        current = 0
        total = limit or (1 << 31) - 1
        limit = min(100, total)

        offset_date = 0
        offset_id = 0
        offset_topic = 0
        seen_topic_ids = set()

        while True:
            result = await self.invoke(
                raw.functions.messages.GetForumTopics(
                    peer=await self.resolve_peer(chat_id),
                    offset_date=offset_date,
                    offset_id=offset_id,
                    offset_topic=offset_topic,
                    limit=limit,
                )
            )

            users = {item.id: item for item in result.users}
            chats = {item.id: item for item in result.chats}
            messages = {}

            for message in result.messages:
                if isinstance(message, raw.types.MessageEmpty):
                    continue
                messages[message.id] = await types.Message._parse(
                    self, message, users, chats
                )

            page_topics = []
            for topic in result.topics:
                parsed_topic = types.ForumTopic._parse(
                    self, topic, messages, users, chats
                )
                if parsed_topic is None or parsed_topic.id in seen_topic_ids:
                    continue
                seen_topic_ids.add(parsed_topic.id)
                page_topics.append(parsed_topic)

            if not page_topics:
                return

            for topic in page_topics:
                yield topic
                current += 1
                if current >= total:
                    return

            last_topic = page_topics[-1]
            if last_topic.top_message is None or last_topic.top_message.date is None:
                return

            offset_id = last_topic.top_message.id
            offset_date = utils.datetime_to_timestamp(last_topic.top_message.date)
            offset_topic = last_topic.id
