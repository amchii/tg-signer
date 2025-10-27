from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class WebUISettings(BaseModel):
    """Configuration shared between the Web UI backend and CLI."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    workdir: Path = Path(".signer")
    tasks_dir_name: str = "signs"
    static_dir: Path = Path(__file__).resolve().parent / "static"
    account: str = "my_account"
    session_dir: Path = Path(".")
    proxy: Optional[dict[str, Any]] = None
    session_string: Optional[str] = None
    in_memory: bool = False

    @property
    def sign_tasks_dir(self) -> Path:
        return self.workdir / self.tasks_dir_name

    @classmethod
    def from_environment(cls) -> "WebUISettings":
        workdir = Path(os.environ.get("TG_SIGNER_WORKDIR", ".signer"))
        session_dir = Path(os.environ.get("TG_SESSION_DIR", "."))
        account = os.environ.get("TG_ACCOUNT", "my_account")
        session_string = os.environ.get("TG_SESSION_STRING")
        in_memory = os.environ.get("TG_IN_MEMORY", "0").lower() in {
            "1",
            "true",
            "yes",
        }
        proxy = None
        return cls(
            workdir=workdir,
            session_dir=session_dir,
            account=account,
            session_string=session_string,
            in_memory=in_memory,
            proxy=proxy,
        )

    @classmethod
    def from_cli_context(cls, ctx: dict) -> "WebUISettings":
        return cls(
            workdir=Path(ctx.get("workdir", ".signer")),
            session_dir=Path(ctx.get("session_dir", ".")),
            account=ctx.get("account", "my_account"),
            proxy=ctx.get("proxy"),
            session_string=ctx.get("session_string"),
            in_memory=ctx.get("in_memory", False),
        )
