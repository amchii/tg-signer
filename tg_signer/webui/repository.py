from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterable, List

from pydantic import ValidationError

from tg_signer.config import SignConfigV3
from tg_signer.core import make_dirs

from .settings import WebUISettings


class SignTaskRepositoryError(RuntimeError):
    """Base class for repository errors."""


class TaskNotFoundError(SignTaskRepositoryError):
    def __init__(self, name: str):
        super().__init__(f"Task '{name}' does not exist.")
        self.name = name


class TaskConflictError(SignTaskRepositoryError):
    def __init__(self, name: str):
        super().__init__(f"Task '{name}' already exists.")
        self.name = name


class ConfigValidationError(SignTaskRepositoryError):
    def __init__(self, errors: Iterable[Any]):
        super().__init__("配置校验失败")
        self.errors = list(errors)


class SignTaskRepository:
    """File-system backed repository for Signer tasks."""

    def __init__(self, settings: WebUISettings):
        self.settings = settings
        self.tasks_dir = make_dirs(settings.sign_tasks_dir)

    def _task_dir(self, name: str) -> Path:
        return self.tasks_dir / name

    def _config_path(self, name: str) -> Path:
        return self._task_dir(name) / "config.json"

    def list_tasks(self) -> List[str]:
        names: List[str] = []
        for path in self.tasks_dir.iterdir():
            if path.is_dir() and not path.name.startswith("."):
                names.append(path.name)
        names.sort()
        return names

    def load_task(self, name: str) -> SignConfigV3:
        config_path = self._config_path(name)
        if not config_path.exists():
            raise TaskNotFoundError(name)
        with config_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        config, from_old = SignConfigV3.load(data)
        if from_old:
            self.save_config(name, config)
        return config

    def save_config(self, name: str, config: SignConfigV3) -> None:
        task_dir = make_dirs(self._task_dir(name))
        with task_dir.joinpath("config.json").open("w", encoding="utf-8") as fp:
            json.dump(config.to_jsonable(), fp, ensure_ascii=False, indent=2)

    def default_config(self) -> SignConfigV3:
        return SignConfigV3.model_validate(
            {
                "sign_at": "06:00:00",
                "random_seconds": 0,
                "sign_interval": 1,
                "chats": [],
            }
        )

    def create_task(self, name: str, payload: dict | None = None) -> SignConfigV3:
        if not name:
            raise ValueError("任务名称不能为空")
        task_dir = self._task_dir(name)
        if task_dir.exists():
            raise TaskConflictError(name)
        try:
            config = self._parse_config(payload)
        except ValidationError as exc:
            raise ConfigValidationError(exc.errors()) from exc
        self.save_config(name, config)
        return config

    def update_task(self, name: str, payload: dict) -> SignConfigV3:
        if not self._task_dir(name).exists():
            raise TaskNotFoundError(name)
        try:
            config = self._parse_config(payload)
        except ValidationError as exc:
            raise ConfigValidationError(exc.errors()) from exc
        self.save_config(name, config)
        return config

    def delete_task(self, name: str) -> None:
        task_dir = self._task_dir(name)
        if not task_dir.exists():
            raise TaskNotFoundError(name)
        shutil.rmtree(task_dir)

    def _parse_config(self, payload: dict | None) -> SignConfigV3:
        if payload is None:
            return self.default_config()
        if not isinstance(payload, dict):
            raise ValueError("配置必须是对象")
        return SignConfigV3.model_validate(payload)
