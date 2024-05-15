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
from urllib import parse

from pyrogram import Client, errors
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
desktop_api_id = 611335
desktop_api_hash = "d524b414d21f4d37f08684c1df41ac9c"
root_dir = pathlib.Path(__file__).parent.absolute()
local_dir = root_dir / ".signer"


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
    return Client(
        name,
        desktop_api_id,
        desktop_api_hash,
        proxy=proxy,
    )


app = get_client()


def get_now():
    return datetime.now(tz=timezone(timedelta(hours=8)))


def make_dirs(path: pathlib.Path, exist_ok=True):
    if not path.is_dir():
        os.makedirs(path, exist_ok=exist_ok)
    return path


@dataclasses.dataclass
class SignConfig:
    chat_id: int
    sign_text: str
    sign_at: time
    random_seconds: float | int

    def to_jsonable(self):
        return {
            "chat_id": self.chat_id,
            "sign_text": self.sign_text,
            "sign_at": self.sign_at.isoformat(),
            "random_seconds": self.random_seconds,
        }

    @classmethod
    def from_json(cls, d) -> "SignConfig":
        return cls(
            int(d["chat_id"]),
            d["sign_text"],
            time.fromisoformat(str(d["sign_at"])),
            d["random_seconds"],
        )


class UserSigner:
    def __init__(self, sign_name: str = None, user: User = None):
        self.sign_name = sign_name
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
        sign_dir = self.signs_dir / str(self.sign_name)
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
            with open(file, "r") as f:
                data = json.load(f)
            data.pop("_")
            user = User(
                id=data["id"],
                is_self=True,
                first_name=data["first_name"],
                last_name=data["last_name"],
            )
            return user

    def set_me(self, user: User):
        self.user = user
        with open(self.base_dir.joinpath("me.json"), "w") as fp:
            fp.write(str(user))

    def ask_for_config(self) -> "SignConfig":
        chat_id = int(input("Chat ID: "))
        sign_text = input("签到文本: ")
        sign_at_str = input("每日签到时间（如 06:00:00）: ")
        sign_at_str = sign_at_str.replace("：", ":").strip()
        sign_at = time.fromisoformat(sign_at_str)
        random_seconds_str = input("签到时间误差随机秒数（默认为0）: ") or "0"
        random_seconds = float(random_seconds_str)
        return SignConfig(chat_id, sign_text, sign_at, random_seconds)

    def reconfig(self):
        config = self.ask_for_config()
        with open(self.config_file, "w") as fp:
            json.dump(config.to_jsonable(), fp)
        return config

    def load_config(self) -> "SignConfig":
        if not self.config_file.exists():
            config = self.reconfig()
        else:
            with open(self.config_file, "r") as fp:
                config = SignConfig.from_json(json.load(fp))
        return config

    def load_sign_record(self):
        sign_record = {}
        if not self.sign_record_file.is_file():
            with open(self.sign_record_file, "w") as fp:
                json.dump(sign_record, fp)
        else:
            with open(self.sign_record_file, "r") as fp:
                sign_record = json.load(fp)
        return sign_record

    async def login(self, num_of_dialogs=20):
        num_of_dialogs = int(
            input(f"获取最近N个对话（默认{num_of_dialogs}）：") or num_of_dialogs
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

            with open(self.base_dir.joinpath("latest_chats.json"), "w") as fp:
                json.dump(
                    latest_chats,
                    fp,
                    indent=4,
                    default=Object.default,
                    ensure_ascii=False,
                )

    def list(self):
        signs = []
        for d in os.listdir(self.signs_dir):
            if self.signs_dir.joinpath(d).is_dir():
                print(d)
                signs.append(d)
        return signs

    async def sign(self, chat_id: int, sign_text: str):
        await app.send_message(chat_id, sign_text)

    async def run(self):
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
                    if str(now.date()) not in sign_record:
                        await self.sign(config.chat_id, config.sign_text)
                        sign_record[str(now.date())] = now.isoformat()
                        with open(self.sign_record_file, "w") as fp:
                            json.dump(sign_record, fp)

                    next_run = (now + timedelta(days=1)).replace(
                        hour=sign_at.hour,
                        minute=sign_at.minute,
                        second=sign_at.second,
                        microsecond=sign_at.microsecond,
                    ) + timedelta(seconds=random.randint(0, config.random_seconds))
                    logger.info(f"下次运行时间: {next_run}")
                    await asyncio.sleep((next_run - now).total_seconds())
            except (OSError, errors.Unauthorized) as e:
                logger.exception(e)
                await asyncio.sleep(30)


async def main():
    help_text = (
        "Usage: tg-signer <command>\n"
        "Available commands: list, login, run, reconfig\n\n"
        "e.g. tg-signer run"
    )
    if len(sys.argv) != 2:
        print(help_text)
        sys.exit(1)
    command = sys.argv[1].strip().lower()
    signer = UserSigner()
    if command == "login":
        return await signer.login()
    elif command == "list":
        return signer.list()
    name = input("签到任务名（e.g. mojie）：")
    signer.sign_name = name
    if command == "run":
        return await signer.run()
    elif command == "reconfig":
        return signer.reconfig()
    print(help_text)
    sys.exit(1)


if __name__ == "__main__":
    app.run(main())
