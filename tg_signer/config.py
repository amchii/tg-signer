import re
from datetime import time
from functools import cached_property
from typing import ClassVar, List, Literal, Optional, Tuple, Type, Union

from pydantic import BaseModel, ValidationError
from pyrogram.types import Message
from typing_extensions import Self, TypeAlias


class BaseJSONConfig(BaseModel):
    version: ClassVar[str] = 0
    olds: ClassVar[Optional[List[Type["BaseJSONConfig"]]]] = None
    is_current: ClassVar[bool] = False

    @classmethod
    def valid(cls, d):
        try:
            instance = cls.model_validate(d)
        except (ValidationError, TypeError):
            return
        return instance

    def to_jsonable(self):
        return self.model_dump(mode="json")

    @classmethod
    def to_current(cls, obj: Self):
        return obj

    @classmethod
    def load(cls, d: dict) -> Tuple[Self, bool]:
        if instance := cls.valid(d):
            return instance, False
        for old in cls.olds or []:
            if old_inst := old.valid(d):
                return old.to_current(old_inst), True


class SignConfigV1(BaseJSONConfig):
    version = 1

    chat_id: int
    sign_text: str
    sign_at: time
    random_seconds: int

    @classmethod
    def to_current(cls, obj):
        return SignConfig(
            chats=[
                SignChat(
                    chat_id=obj.chat_id,
                    sign_text=obj.sign_text,
                    delete_after=None,
                )
            ],
            sign_at=obj.sign_at,
            random_seconds=obj.random_seconds,
        )


class SignChat(BaseJSONConfig):
    chat_id: int
    sign_text: str
    delete_after: Optional[int] = None


class SignConfigV2(BaseJSONConfig):
    version: ClassVar = 2
    olds: ClassVar = [SignConfigV1]
    is_current: ClassVar = True

    chats: List[SignChat]
    sign_at: time
    random_seconds: int


SignConfig = SignConfigV2

MatchRuleT: TypeAlias = Literal["exact", "contains", "regex"]


class MatchConfig(BaseJSONConfig):
    chat_id: Union[int, str] = None  # 聊天id或username
    rule: MatchRuleT = "exact"  # 匹配规则
    rule_value: str  # 规则值
    from_user_ids: Optional[List[Union[int, str]]] = (
        None  # 发送者id或username，为空时，匹配所有人
    )
    default_send_text: Optional[str] = None  # 默认发送内容
    send_text_search_regex: Optional[str] = None  # 用正则表达式从消息中提取发送内容
    delete_after: Optional[int] = None
    ignore_case: bool = True  # 忽略大小写

    def __str__(self):
        return (
            f"{self.__class__.__name__}(chat_id={self.chat_id}, rule={self.rule}, rule_value={self.rule_value}),"
            f" default_send_text={self.default_send_text}, send_text_search_regex={self.send_text_search_regex}"
        )

    @cached_property
    def from_user_set(self):
        return set(
            (
                "me"
                if u in ["me", "self"]
                else u.lower().strip("@") if isinstance(u, str) else u
            )
            for u in self.from_user_ids
        )

    def match_user(self, message: "Message"):
        if not self.from_user_ids:
            return True
        if not message.from_user:
            return True
        return (
            message.from_user.id in self.from_user_set
            or (
                message.from_user.username
                and message.from_user.username.lower() in self.from_user_set
            )
            or ("me" in self.from_user_set and message.from_user.is_self)
        )

    def match_text(self, text: str) -> bool:
        """
        根据`rule`校验`text`是否匹配
        """
        rule_value = self.rule_value
        if self.rule == "exact":
            if self.ignore_case:
                return rule_value.lower() == text.lower()
            return rule_value == text
        elif self.rule == "contains":
            if self.ignore_case:
                return rule_value.lower() in text.lower()
            return rule_value in text
        elif self.rule == "regex":
            flags = re.IGNORECASE if self.ignore_case else 0
            return bool(re.search(rule_value, text, flags=flags))
        return False

    def match(self, message: "Message"):
        return bool(self.match_user(message) and self.match_text(message.text))

    def get_send_text(self, text: str):
        send_text = self.default_send_text
        if self.send_text_search_regex:
            m = re.search(self.send_text_search_regex, text)
            if not m:
                return send_text
            try:
                send_text = m.group(1)
            except IndexError:
                raise ValueError(
                    f"{self}: 消息文本: 「{text}」匹配成功但未能捕获关键词, 请检查正则表达式"
                )
        return send_text


class MonitorConfig(BaseJSONConfig):
    """监控配置"""

    version: ClassVar = 1
    is_current: ClassVar = True
    match_cfgs: List[MatchConfig]

    @property
    def chat_ids(self):
        return [cfg.chat_id for cfg in self.match_cfgs]
