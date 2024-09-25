import asyncio
import dataclasses
import json
import logging
import os
import pathlib
import random
import sys
from datetime import datetime, time, timedelta, timezone
from logging.handlers import RotatingFileHandler
from typing import List, TypedDict
from urllib import parse

from pyrogram import Client as BaseClient, errors
from pyrogram.types import Object, User

format_str = (
    "[%(levelname)s] [%(name)s] %(asctime)s %(filename)s %(lineno)s %(message)s"
)
logging.basicConfig(
    level=logging.INFO,
    format=format_str,
)

logger = logging.getLogger("tg-signer")
formatter = logging.Formatter(format_str)
file_handler = RotatingFileHandler(
    "tg-signer.log",
    maxBytes=1024 * 1024 * 3,
    backupCount=10,
    encoding="utf-8",
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
root_dir = pathlib.Path(".").absolute()
local_dir = root_dir / ".signer"


class Client(BaseClient):
    async def __aenter__(self):
        try:
            return await self.start()
        except ConnectionError:
            pass


def get_api_config():
    api_id = int(os.environ.get("TG_API_ID", 611335))
    api_hash = os.environ.get("TG_API_HASH", "d524b414d21f4d37f08684c1df41ac9c")
    return api_id, api_hash


def get_proxy():
    if tg_proxy := os.environ.get("TG_PROXY"):
        r = parse.urlparse(tg_proxy)
        return {
            "scheme": r.scheme,
            "hostname": r.hostname,
            "port": r.port,
            "username": r.username,
            "password": r.password,
        }


def get_client(name: str = "my_account", proxy=None):
    proxy = proxy or get_proxy()
    api_id, api_hash = get_api_config()
    return Client(name, api_id, api_hash, proxy=proxy, workdir=".")


app = get_client()


def get_now():
    return datetime.now(tz=timezone(timedelta(hours=8)))


def make_dirs(path: pathlib.Path, exist_ok=True):
    if not path.is_dir():
        os.makedirs(path, exist_ok=exist_ok)
    return path


class SignChat(TypedDict):
    chat_id: int
    sign_text: str


@dataclasses.dataclass
class SignConfig:
    chats: List[SignChat]
    sign_at: time
    random_seconds: int

    def to_jsonable(self):
        return {
            "chats": self.chats,
            "sign_at": self.sign_at.isoformat(),
            "random_seconds": self.random_seconds,
        }

    @classmethod
    def from_json(cls, d) -> "SignConfig":
        if "chats" in d:
            return cls(
                chats=d["chats"],
                sign_at=time.fromisoformat(str(d["sign_at"])),
                random_seconds=d["random_seconds"],
            )
        else:
            return cls(
                chats=[{"chat_id": d["chat_id"], "sign_text": d["sign_text"]}],
                sign_at=time.fromisoformat(str(d["sign_at"])),
                random_seconds=d["random_seconds"],
            )


class UserSigner:
    def __init__(self, task_name: str = None, user: User = None):
        self.task_name = task_name
        self.user = user or self.get_me()

    @property
    def base_dir(self):
        base_dir = root_dir / ".signer"
        make_dirs(base_dir)
        return base_dir

    @property
    def signs_dir(self):
        signs_dir = self.base_dir / "signs"
        make_dirs(signs_dir)
        return signs_dir

    @property
    def sign_dir(self):
        sign_dir = self.signs_dir / str(self.task_name)
        make_dirs(sign_dir)
        return sign_dir

    @property
    def sign_record_file(self):
        return self.sign_dir.joinpath("sign_record.json")

    @property
    def config_file(self):
        return self.sign_dir.joinpath("config.json")

    def get_me(self):
        file = self.base_dir.joinpath("me.json")
        if file.is_file():
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.pop("_")
            user = User(
                id=data["id"],
                is_self=True,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
            )
            return user

    def set_me(self, user: User):
        self.user = user
        with open(self.base_dir.joinpath("me.json"), "w", encoding="utf-8") as fp:
            fp.write(str(user))

    def ask_for_config(self) -> "SignConfig":
        chats = []
        i = 1
        print(f"开始配置任务<{self.task_name}>")
        while True:
            print(f"第{i}个签到")
            chat_id = int(input("Chat ID（登录时最近对话输出中的ID）: "))
            sign_text = input("签到文本（如 /sign）: ") or "/sign"
            chats.append(
                {
                    "chat_id": chat_id,
                    "sign_text": sign_text,
                }
            )
            continue_ = input("继续配置签到？(y/N)：")
            if continue_.strip().lower() != "y":
                break
            i += 1
        sign_at_str = input("每日签到时间（如 06:00:00）: ") or "06:00:00"
        sign_at_str = sign_at_str.replace("：", ":").strip()
        sign_at = time.fromisoformat(sign_at_str)
        random_seconds_str = input("签到时间误差随机秒数（默认为0）: ") or "0"
        random_seconds = int(float(random_seconds_str))
        return SignConfig(chats, sign_at, random_seconds)

    def reconfig(self):
        config = self.ask_for_config()
        with open(self.config_file, "w", encoding="utf-8") as fp:
            json.dump(config.to_jsonable(), fp)
        return config

    def load_config(self) -> "SignConfig":
        if not self.config_file.exists():
            config = self.reconfig()
        else:
            with open(self.config_file, "r", encoding="utf-8") as fp:
                config = SignConfig.from_json(json.load(fp))
        return config

    def load_sign_record(self):
        sign_record = {}
        if not self.sign_record_file.is_file():
            with open(self.sign_record_file, "w", encoding="utf-8") as fp:
                json.dump(sign_record, fp)
        else:
            with open(self.sign_record_file, "r", encoding="utf-8") as fp:
                sign_record = json.load(fp)
        return sign_record

    async def login(self, num_of_dialogs=20):
        num_of_dialogs = int(
            input(
                f"获取最近N个对话（默认{num_of_dialogs}，请确保想要签到的对话在最近N个对话内）："
            )
            or num_of_dialogs
        )
        async with app:
            me = await app.get_me()
            self.set_me(me)
            latest_chats = []
            async for dialog in app.get_dialogs(num_of_dialogs):
                chat = dialog.chat
                latest_chats.append(
                    {
                        "id": chat.id,
                        "title": chat.title,
                        "type": chat.type,
                        "username": chat.username,
                        "first_name": chat.first_name,
                        "last_name": chat.last_name,
                    }
                )
                print(latest_chats[-1])

            with open(
                self.base_dir.joinpath("latest_chats.json"), "w", encoding="utf-8"
            ) as fp:
                json.dump(
                    latest_chats,
                    fp,
                    indent=4,
                    default=Object.default,
                    ensure_ascii=False,
                )

    def list_(self):
        signs = []
        print("已配置的任务：")
        for d in os.listdir(self.signs_dir):
            if self.signs_dir.joinpath(d).is_dir():
                print(d)
                signs.append(d)
        return signs

    async def sign(self, chat_id: int, sign_text: str):
        await app.send_message(chat_id, sign_text)

    async def run(self, only_once: bool = False):
        """
        :param only_once: 只运行一次
        """
        if self.user is None:
            await self.login()

        config = self.load_config()
        sign_record = self.load_sign_record()
        sign_at = config.sign_at
        while True:
            try:
                async with app:
                    now = get_now()
                    logger.info(f"当前时间: {now}")
                    now_date_str = str(now.date())
                    if now_date_str not in sign_record:
                        for chat in config.chats:
                            await self.sign(chat["chat_id"], chat["sign_text"])
                        sign_record[now_date_str] = now.isoformat()
                        with open(self.sign_record_file, "w", encoding="utf-8") as fp:
                            json.dump(sign_record, fp)
                    else:
                        print(
                            f"当前任务今日已签到，签到时间: {sign_record[now_date_str]}"
                        )

            except (OSError, errors.Unauthorized) as e:
                logger.exception(e)
                await asyncio.sleep(30)
                continue

            if only_once:
                break

            next_run = (now + timedelta(days=1)).replace(
                hour=sign_at.hour,
                minute=sign_at.minute,
                second=sign_at.second,
                microsecond=sign_at.microsecond,
            ) + timedelta(seconds=random.randint(0, int(config.random_seconds)))
            logger.info(f"下次运行时间: {next_run}")
            await asyncio.sleep((next_run - now).total_seconds())

    async def run_once(self):
        return await self.run(only_once=True)

    async def send_text(self, chat_id: int, text: str):
        if self.user is None:
            await self.login()
        async with app:
            await app.send_message(chat_id, text)
        print("发送成功")


async def main():
    help_text = (
        "Usage: tg-signer <command> [task_name]...\n"
        "Available commands: list, login, run, run_once, reconfig, send_message\n"
        " list: 列出已有配置\n"
        " login: 登录账号（用于获取session）\n"
        " run: 根据配置运行签到\n"
        " run_once: 运行一次签到（可以传额外参数进行配置覆盖）\n"
        " reconfig: 重新配置\n"
        " send_text: 发送一次消息\n"
        "\n"
        "e.g.:\n"
        " tg-signer run\n"
        " tg-signer run my_sign  # 不询问直接运行'my_sign'任务\n"
        " tg-signer run_once my_sign  # 直接运行一次'my_sign'任务\n"
        " tg-signer send_text 8671234001 /test  # 向chat_id为'8671234001'的聊天发送'/test'文本"
    )
    if len(sys.argv) < 2:
        print(help_text)
        sys.exit(1)
    command = sys.argv[1].strip().lower()
    signer = UserSigner()
    if command == "list":
        return signer.list_()
    signer.list_()
    if command == "login":
        return await signer.login()
    if command == "send_text":
        if len(sys.argv) != 4:
            print("Usage: tg-signer send_text <chat_id> <text>")
            sys.exit(1)
        chat_id = int(sys.argv[2])
        text = sys.argv[3]
        return await signer.send_text(chat_id, text)
    if len(sys.argv) == 3:
        task_name = sys.argv[2]
    else:
        task_name = input("签到任务名（e.g. my_sign）：") or "my_sign"
    signer.task_name = task_name
    if command == "run":
        return await signer.run()
    elif command == "reconfig":
        return signer.reconfig()
    elif command == "run_once":
        return await signer.run_once()
    print(help_text)
    sys.exit(1)


if __name__ == "__main__":
    app.run(main())
