from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, Field


class TaskSummary(BaseModel):
    name: str


class TaskListResponse(BaseModel):
    tasks: List[TaskSummary]


class SignTaskCreateRequest(BaseModel):
    name: str = Field(..., description="任务名称")
    config: dict[str, Any] | None = Field(
        default=None, description="SignConfigV3 兼容的配置"
    )


class SignTaskUpdateRequest(BaseModel):
    config: dict[str, Any] = Field(..., description="SignConfigV3 兼容的配置")


class SignTaskResponse(BaseModel):
    name: str
    config: dict[str, Any]


class ActionMeta(BaseModel):
    value: int
    key: str
    label: str
    requires_text: bool = False


class ActionMetaResponse(BaseModel):
    actions: List[ActionMeta]
