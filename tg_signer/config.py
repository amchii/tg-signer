import re
from datetime import time
from enum import Enum
from functools import cached_property
from typing import (
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
)

from pydantic import AnyHttpUrl, BaseModel, ValidationError
from pyrogram.types import Chat, Message
from typing_extensions import Self, TypeAlias


def get_display_width(text: str) -> int:
    """计算文本在终端中的显示宽度（考虑中文字符占2个字符位）"""
    width = 0
    for char in text:
        if ord(char) > 127:  # 非ASCII字符（包括中文）
            width += 2
        else:
            width += 1
    return width


def pad_text_to_width(text: str, target_width: int, align: str = "left") -> str:
    """将文本填充到指定宽度"""
    current_width = get_display_width(text)
    padding_needed = target_width - current_width

    if padding_needed <= 0:
        return text

    if align == "left":
        return text + " " * padding_needed
    elif align == "right":
        return " " * padding_needed + text
    else:  # center
        left_padding = padding_needed // 2
        right_padding = padding_needed - left_padding
        return " " * left_padding + text + " " * right_padding


class BaseJSONConfig(BaseModel):
    version: ClassVar[Union[str, int]] = 0
    olds: ClassVar[Optional[List[Type["BaseJSONConfig"]]]] = None
    is_current: ClassVar[bool] = False

    @classmethod
    def valid(cls, d):
        try:
            instance = cls.model_validate(d)
        except (ValidationError, TypeError):
            return None
        return instance

    def to_jsonable(self):
        return self.model_dump(mode="json")

    @classmethod
    def to_current(cls, obj: Self):
        return obj

    @classmethod
    def load(cls, d: dict) -> Optional[Tuple[Self, bool]]:
        if instance := cls.valid(d):
            return instance, False
        for old in cls.olds or []:
            if old_inst := old.valid(d):
                return old.to_current(old_inst), True
        return None


class SignConfigV1(BaseJSONConfig):
    version = 1

    chat_id: int
    sign_text: str
    sign_at: time
    random_seconds: int

    @classmethod
    def to_current(cls, obj: "SignConfigV1"):
        return SignConfigV2(
            chats=[
                SignChatV2(
                    chat_id=obj.chat_id,
                    sign_text=obj.sign_text,
                    delete_after=None,
                )
            ],
            sign_at=str(obj.sign_at),
            random_seconds=obj.random_seconds,
        )


class SignChatV2(BaseJSONConfig):
    version: ClassVar = 2
    chat_id: int
    delete_after: Optional[int] = None
    sign_text: Union[str, Literal["🎲", "🎯", "🏀", "⚽", "🎳", "🎰"]]
    as_dice: bool = False  # 作为Dice类型的emoji进行发送
    text_of_btn_to_click: Optional[str] = None  # 需要点击的按钮的文本
    choose_option_by_image: bool = False  # 需要根据图片选择选项
    has_calculation_problem: bool = False  # 是否有计算题

    @property
    def need_response(self):
        return (
            bool(self.text_of_btn_to_click)
            or self.choose_option_by_image
            or self.has_calculation_problem
        )


class SignConfigV2(BaseJSONConfig):
    version: ClassVar = 2
    olds: ClassVar = [SignConfigV1]
    is_current: ClassVar = False

    chats: List[SignChatV2]
    sign_at: str  # 签到时间，time或crontab表达式
    random_seconds: int = 0
    sign_interval: int = 1  # 连续签到的间隔时间，单位秒

    @classmethod
    def to_current(cls, obj: Union["SignConfigV2", "SignConfigV1"]):
        if isinstance(obj, SignConfigV1):
            obj = SignConfigV1.to_current(obj)
        v3_chats = []
        for chat in obj.chats:
            actions = []
            if chat.sign_text:
                if chat.as_dice:
                    actions.append(SendDiceAction(dice=chat.sign_text))
                else:
                    actions.append(SendTextAction(text=chat.sign_text))
            if chat.text_of_btn_to_click:
                actions.append(
                    ClickKeyboardByTextAction(text=chat.text_of_btn_to_click)
                )
            if chat.choose_option_by_image:
                actions.append(ChooseOptionByImageAction())
            if chat.has_calculation_problem:
                actions.append(ReplyByCalculationProblemAction())
            v3_chats.append(
                SignChatV3(
                    chat_id=chat.chat_id,
                    delete_after=chat.delete_after,
                    actions=actions,
                )
            )
        return SignConfigV3(
            sign_at=obj.sign_at,
            random_seconds=obj.random_seconds,
            sign_interval=obj.sign_interval,
            chats=v3_chats,
        )


class SupportAction(int, Enum):
    SEND_TEXT = 1  # 发送普通文本
    SEND_DICE = 2  # 发送Dice类型的emoji
    CLICK_KEYBOARD_BY_TEXT = 3  # 根据文本点击键盘
    CHOOSE_OPTION_BY_IMAGE = 4  # 根据图片选择选项
    REPLY_BY_CALCULATION_PROBLEM = 5  # 回复计算题

    @property
    def desc(self):
        return {
            SupportAction.SEND_TEXT: "发送普通文本",
            SupportAction.SEND_DICE: "发送Dice类型的emoji",
            SupportAction.CLICK_KEYBOARD_BY_TEXT: "根据文本点击键盘",
            SupportAction.CHOOSE_OPTION_BY_IMAGE: "根据图片选择选项",
            SupportAction.REPLY_BY_CALCULATION_PROBLEM: "回复计算题",
        }[self]


class SignAction(BaseModel):
    action: SupportAction


class SendTextAction(SignAction):
    action: Literal[SupportAction.SEND_TEXT] = SupportAction.SEND_TEXT
    text: str


class SendDiceAction(SignAction):
    action: Literal[SupportAction.SEND_DICE] = SupportAction.SEND_DICE
    dice: Union[Literal["🎲", "🎯", "🏀", "⚽", "🎳", "🎰"], str]


class ClickKeyboardByTextAction(SignAction):
    action: Literal[SupportAction.CLICK_KEYBOARD_BY_TEXT] = (
        SupportAction.CLICK_KEYBOARD_BY_TEXT
    )
    text: str


class ChooseOptionByImageAction(SignAction):
    action: Literal[SupportAction.CHOOSE_OPTION_BY_IMAGE] = (
        SupportAction.CHOOSE_OPTION_BY_IMAGE
    )


class ReplyByCalculationProblemAction(SignAction):
    action: Literal[SupportAction.REPLY_BY_CALCULATION_PROBLEM] = (
        SupportAction.REPLY_BY_CALCULATION_PROBLEM
    )


ActionT: TypeAlias = Union[
    SendTextAction,
    SendDiceAction,
    ClickKeyboardByTextAction,
    ChooseOptionByImageAction,
    ReplyByCalculationProblemAction,
]


class SignChatV3(BaseJSONConfig):
    version: ClassVar = 3
    chat_id: int
    name: Optional[str] = None
    delete_after: Optional[int] = None
    actions: List[ActionT]
    action_interval: float = 1  # actions的间隔时间，单位秒

    def __repr__(self) -> str:
        return (
            f"SignChatV3(chat_id={self.chat_id}, "
            f"delete_after={self.delete_after}, "
            f"actions=[{len(self.actions)} actions]),"
            f"action_interval={self.action_interval}"
        )

    def __str__(self) -> str:
        # 设置总宽度（不包括边框字符）
        content_width = 48

        # 构建边框
        top_border = "╔" + "═" * content_width + "╗"
        bottom_border = "╚" + "═" * content_width + "╝"
        separator = "╟" + "─" * content_width + "╢"

        # 构建标题部分
        chat_id_text = f"Chat ID: {self.chat_id}"
        title = f"║ {pad_text_to_width(chat_id_text, content_width - 2)} ║"

        # 构建name部分
        name_text = f"Name: {self.name or '-'}"
        name_info = f"║ {pad_text_to_width(name_text, content_width - 2)} ║"

        # 构建删除时间部分
        delete_text = f"Delete After: {self.delete_after or '-'}"
        delete_info = f"║ {pad_text_to_width(delete_text, content_width - 2)} ║"

        # 构建actions部分
        actions_header_text = "Actions Flow:"
        actions_header = (
            f"║ {pad_text_to_width(actions_header_text, content_width - 2)} ║"
        )
        actions_lines = []

        for i, action in enumerate(self.actions, 1):
            action_type = action.action.desc
            details = ""

            if isinstance(action, SendTextAction):
                text_preview = (
                    action.text[:15] + "..." if len(action.text) > 15 else action.text
                )
                details = f"Text: {text_preview}"
            elif isinstance(action, SendDiceAction):
                details = f"Dice: {action.dice}"
            elif isinstance(action, ClickKeyboardByTextAction):
                text_preview = (
                    action.text[:15] + "..." if len(action.text) > 15 else action.text
                )
                details = f"Click: {text_preview}"

            if details:
                action_text = f"{i}. [{action_type}] {details}"
            else:
                action_text = f"{i}. [{action_type}]"

            action_line = f"║ {pad_text_to_width(action_text, content_width - 2)} ║"
            actions_lines.append(action_line)

        # 组合所有部分
        result = [
            top_border,
            title,
            name_info,
            delete_info,
            separator,
            actions_header,
            *actions_lines,
            bottom_border,
        ]

        return "\n".join(result)

    @property
    def requires_ai(self) -> bool:
        ai_actions = {
            SupportAction.CHOOSE_OPTION_BY_IMAGE,
            SupportAction.REPLY_BY_CALCULATION_PROBLEM,
        }
        return any(action.action in ai_actions for action in self.actions)


class SignConfigV3(BaseJSONConfig):
    version: ClassVar = 3
    olds: ClassVar = [SignConfigV2]
    is_current: ClassVar = True

    _version: Literal[3] = 3
    chats: List[SignChatV3]
    sign_at: str  # 签到时间，time或crontab表达式
    random_seconds: int = 0
    sign_interval: int = 1  # 连续签到的间隔时间，单位秒

    @property
    def requires_ai(self) -> bool:
        return any(chat.requires_ai for chat in self.chats)


MatchRuleT: TypeAlias = Literal["exact", "contains", "regex", "all"]


class UDPForward(BaseModel):
    type: Literal["udp"] = "udp"
    host: str
    port: int


class HttpCallback(BaseModel):
    type: Literal["http"] = "http"
    url: AnyHttpUrl
    headers: Optional[Dict[str, str]] = None
    method: Literal["post"] = "post"


class MatchConfig(BaseJSONConfig):
    chat_id: Union[int, str] = None  # 聊天id或username
    rule: MatchRuleT = "exact"  # 匹配规则
    rule_value: Optional[str] = None  # 规则值
    from_user_ids: Optional[List[Union[int, str]]] = (
        None  # 发送者id或username，为空时，匹配所有人
    )
    always_ignore_me: bool = False  # 总是忽略自己发送的消息
    default_send_text: Optional[str] = None  # 默认发送内容
    ai_reply: bool = False  # 是否使用AI回复
    ai_prompt: Optional[str] = None
    send_text_search_regex: Optional[str] = None  # 用正则表达式从消息中提取发送内容
    delete_after: Optional[int] = None
    ignore_case: bool = True  # 忽略大小写
    forward_to_chat_id: Optional[Union[int, str]] = (
        None  # 转发消息到该聊天，默认为消息来源
    )
    external_forwards: Optional[List[Union[UDPForward, HttpCallback]]] = (
        None  # 转发到外部
    )
    push_via_server_chan: bool = False  # 将消息通过server酱推送
    server_chan_send_key: Optional[str] = None  # server酱的sendkey

    def __str__(self):
        return (
            f"{self.__class__.__name__}(chat_id={self.chat_id}, rule={self.rule}, rule_value={self.rule_value}),"
            f" default_send_text={self.default_send_text}, send_text_search_regex={self.send_text_search_regex}"
        )

    @cached_property
    def from_user_set(self):
        return {
            (
                "me"
                if u in ["me", "self"]
                else u.lower().strip("@")
                if isinstance(u, str)
                else u
            )
            for u in self.from_user_ids
        }

    def match_user(self, message: "Message"):
        if not message.from_user:
            return True
        if self.always_ignore_me and message.from_user.is_self:
            return False
        if not self.from_user_ids:
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
        if self.rule == "all":
            return True
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

    def match_chat(self, chat: "Chat"):
        if isinstance(self.chat_id, int):
            return self.chat_id == chat.id
        return self.chat_id == chat.username

    def match(self, message: "Message"):
        return self.match_chat(message.chat) and bool(
            self.match_user(message) and self.match_text(message.text)
        )

    def get_send_text(self, text: str) -> str:
        send_text = self.default_send_text
        if self.send_text_search_regex:
            m = re.search(self.send_text_search_regex, text)
            if not m:
                return send_text
            try:
                send_text = m.group(1)
            except IndexError as e:
                raise ValueError(
                    f"{self}: 消息文本: 「{text}」匹配成功但未能捕获关键词, 请检查正则表达式"
                ) from e
        return send_text

    @property
    def requires_ai(self) -> bool:
        return bool(self.ai_reply and self.ai_prompt)


class MonitorConfig(BaseJSONConfig):
    """监控配置"""

    version: ClassVar = 1
    is_current: ClassVar = True
    match_cfgs: List[MatchConfig]

    @property
    def chat_ids(self):
        return [cfg.chat_id for cfg in self.match_cfgs]

    @property
    def requires_ai(self) -> bool:
        return any(cfg.requires_ai for cfg in self.match_cfgs)
