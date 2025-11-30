import json
import os
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

from tg_signer.config import BaseJSONConfig, MonitorConfig, SignConfigV3

ConfigKind = Literal["signer", "monitor"]

CONFIG_META: dict[ConfigKind, Tuple[str, type[BaseJSONConfig]]] = {
    "signer": ("signs", SignConfigV3),
    "monitor": ("monitors", MonitorConfig),
}

DEFAULT_WORKDIR = Path(os.environ.get("TG_SIGNER_WORKDIR", ".signer"))
LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = LOG_DIR / "tg-signer.log"


@dataclass
class ConfigEntry:
    name: str
    path: Path
    updated_from_old: bool
    payload: Dict[str, Any]
    cfg: BaseJSONConfig


@dataclass
class UserInfo:
    user_id: str
    data: Dict[str, Any]
    path: Path
    latest_chats: List[Dict[str, Any]] = None


@dataclass
class SignRecord:
    task: str
    user_id: Optional[str]
    records: List[Tuple[str, str]]
    path: Path


def get_workdir(workdir: Optional[Path | str] = None) -> Path:
    base = Path(workdir) if workdir else DEFAULT_WORKDIR
    base.mkdir(parents=True, exist_ok=True)
    return base


def _config_root(kind: ConfigKind, workdir: Optional[Path | str]) -> Path:
    base = get_workdir(workdir)
    dir_name, _ = CONFIG_META[kind]
    return base / dir_name


def _config_path(kind: ConfigKind, name: str, workdir: Optional[Path | str]) -> Path:
    return _config_root(kind, workdir) / name / "config.json"


def list_task_names(
    kind: ConfigKind, workdir: Optional[Path | str] = None
) -> List[str]:
    root = _config_root(kind, workdir)
    if not root.is_dir():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def load_config(
    kind: ConfigKind, name: str, workdir: Optional[Path | str] = None
) -> ConfigEntry:
    config_file = _config_path(kind, name, workdir)
    if not config_file.is_file():
        raise FileNotFoundError(f"配置不存在: {config_file}")
    cfg_cls = CONFIG_META[kind][1]
    with open(config_file, "r", encoding="utf-8") as fp:
        raw = json.load(fp)
    loaded = cfg_cls.load(raw)
    if loaded is None:
        raise ValueError(f"无法解析配置: {config_file}")
    cfg, from_old = loaded
    if from_old:
        # keep the latest structure aligned with current schema
        save_config(kind, name, cfg, workdir=workdir)
    payload = cfg.to_jsonable()
    return ConfigEntry(
        name=name, path=config_file, updated_from_old=from_old, payload=payload, cfg=cfg
    )


def save_config(
    kind: ConfigKind,
    name: str,
    content: Dict[str, Any] | str | BaseJSONConfig,
    workdir: Optional[Path | str] = None,
) -> Path:
    cfg_cls = CONFIG_META[kind][1]
    if isinstance(content, BaseJSONConfig):
        cfg = content
    else:
        data = json.loads(content) if isinstance(content, str) else content
        loaded = cfg_cls.load(data)
        if loaded is None:
            raise ValueError("配置校验失败")
        cfg, _ = loaded
    config_file = _config_path(kind, name, workdir)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as fp:
        json.dump(cfg.to_jsonable(), fp, ensure_ascii=False, indent=2)
    return config_file


def delete_config(
    kind: ConfigKind, name: str, workdir: Optional[Path | str] = None
) -> Path:
    config_file = _config_path(kind, name, workdir)
    if not config_file.exists():
        raise FileNotFoundError(f"配置不存在: {config_file}")
    config_file.unlink()
    parent = config_file.parent
    # remove empty directories only; keep records if present
    try:
        next(parent.iterdir())
    except StopIteration:
        parent.rmdir()
    return config_file


def load_user_infos(workdir: Optional[Path | str] = None) -> List[UserInfo]:
    base = get_workdir(workdir)
    users_dir = base / "users"
    if not users_dir.is_dir():
        return []
    entries: List[UserInfo] = []
    for user_dir in sorted(
        [p for p in users_dir.iterdir() if p.is_dir()], key=lambda p: p.name
    ):
        me_file = user_dir / "me.json"
        if not me_file.is_file():
            continue
        with open(me_file, "r", encoding="utf-8") as fp:
            try:
                data = json.load(fp)
            except json.JSONDecodeError:
                continue

        latest_chats = []
        chats_file = user_dir / "latest_chats.json"
        if chats_file.is_file():
            with open(chats_file, "r", encoding="utf-8") as fp:
                try:
                    latest_chats = json.load(fp)
                except json.JSONDecodeError:
                    pass

        entries.append(
            UserInfo(
                user_id=user_dir.name,
                data=data,
                path=me_file,
                latest_chats=latest_chats,
            )
        )
    return entries


def _record_target(path: Path, signs_root: Path) -> Tuple[str, Optional[str]]:
    relative_parts = path.relative_to(signs_root).parts
    task = relative_parts[0]
    user_id = None
    if len(relative_parts) > 2:
        user_id = relative_parts[1]
    return task, user_id


def load_sign_records(workdir: Optional[Path | str] = None) -> List[SignRecord]:
    base = get_workdir(workdir)
    signs_dir = base / "signs"
    if not signs_dir.is_dir():
        return []
    records: List[SignRecord] = []
    for record_file in sorted(signs_dir.rglob("sign_record.json")):
        try:
            with open(record_file, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except (json.JSONDecodeError, OSError):
            continue
        task, user_id = _record_target(record_file, signs_dir)
        items: Iterable[Tuple[str, str]] = (
            data.items() if isinstance(data, dict) else []
        )
        sorted_items = sorted(items, key=lambda kv: kv[0], reverse=True)
        records.append(
            SignRecord(
                task=task, user_id=user_id, records=sorted_items, path=record_file
            )
        )
    return records


def tail_file(path: Path, limit: int = 200) -> List[str]:
    if not path.is_file():
        return []
    if limit <= 0:
        return []

    buffer: deque[str] = deque()
    chunk_size = 8192

    # Read from the end in chunks to avoid loading large files entirely.
    with open(path, "rb") as fp:
        fp.seek(0, os.SEEK_END)
        position = fp.tell()
        leftover = b""
        while position > 0 and len(buffer) < limit:
            read_size = min(chunk_size, position)
            position -= read_size
            fp.seek(position)
            chunk = fp.read(read_size)
            data = chunk + leftover
            lines = data.split(b"\n")
            leftover = lines[0]
            for line in reversed(lines[1:]):
                buffer.appendleft(line.decode("utf-8", errors="ignore").rstrip("\r"))
                if len(buffer) >= limit:
                    break

        if len(buffer) < limit and leftover:
            buffer.appendleft(leftover.decode("utf-8", errors="ignore").rstrip("\r"))

    return list(buffer)


def list_log_files(log_dir: Optional[Path | str] = None) -> List[Path]:
    base = Path(log_dir) if log_dir else LOG_DIR
    if not base.is_dir():
        return []
    return sorted(p for p in base.glob("*.log") if p.is_file())


def _resolve_log_path(log_path: Optional[Path | str] = None) -> Path:
    if log_path:
        path = Path(log_path).expanduser()
        if not path.is_absolute() and path.parent == Path("."):
            return LOG_DIR / path
        return path
    return DEFAULT_LOG_FILE


def load_logs(
    limit: int = 200, log_path: Optional[Path | str] = None
) -> Tuple[Path, List[str]]:
    path = _resolve_log_path(log_path)
    return path, tail_file(path, limit=limit)
