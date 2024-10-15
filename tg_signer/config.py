from datetime import time
from typing import ClassVar, List, Optional, Self, Tuple, Type

from pydantic import BaseModel, ValidationError


class BaseJSONConfig(BaseModel):
    version: ClassVar[str] = 0
    olds: ClassVar[Optional[List[Type["BaseJSONConfig"]]]] = None
    is_current: ClassVar[bool] = False

    @classmethod
    def match(cls, d):
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
        if instance := cls.match(d):
            return instance, False
        for old in cls.olds or []:
            if old_inst := old.match(d):
                return old.to_current(old_inst), True


class SignChat(BaseJSONConfig):
    chat_id: int
    sign_text: str
    delete_after: Optional[int] = None


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


class SignConfigV2(BaseJSONConfig):
    version: ClassVar = 2
    olds: ClassVar = [SignConfigV1]
    is_current: ClassVar = True

    chats: List[SignChat]
    sign_at: time
    random_seconds: int


SignConfig = SignConfigV2
