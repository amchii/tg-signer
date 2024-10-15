import asyncio
import json
import logging
import os
import pathlib
import random
from datetime import datetime, time, timedelta, timezone
from urllib import parse

from pyrogram import Client as BaseClient, errors
from pyrogram.types import Object, User

from tg_signer.config import SignConfig

logger = logging.getLogger("tg-signer")


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


def get_proxy(proxy: str = None):
    proxy = proxy or os.environ.get("TG_PROXY")
    if proxy:
        r = parse.urlparse(proxy)
        return {
            "scheme": r.scheme,
            "hostname": r.hostname,
            "port": r.port,
            "username": r.username,
            "password": r.password,
        }


def get_client(name: str = "my_account", proxy: dict = None, workdir="."):
    proxy = proxy or get_proxy()
    api_id, api_hash = get_api_config()
    return Client(name, api_id, api_hash, proxy=proxy, workdir=workdir)


def get_now():
    return datetime.now(tz=timezone(timedelta(hours=8)))


def make_dirs(path: pathlib.Path, exist_ok=True):
    if not path.is_dir():
        os.makedirs(path, exist_ok=exist_ok)
    return path


class UserSigner:
    def __init__(
        self,
        task_name: str = None,
        session_dir: str = ".",
        account: str = "my_account",
        proxy=None,
        workdir=".signer",
    ):
        self.task_name = task_name
        self._session_dir = session_dir
        self._account = account
        self._proxy = proxy
        self._workdir = pathlib.Path(workdir)
        self.app = get_client(account, proxy, session_dir)
        self.user = None

    @property
    def workdir(self):
        workdir = self._workdir
        make_dirs(workdir)
        return workdir

    @property
    def signs_dir(self):
        signs_dir = self.workdir / "signs"
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
        file = self.workdir.joinpath("me.json")
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
        with open(self.workdir.joinpath("me.json"), "w", encoding="utf-8") as fp:
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
        return SignConfig.model_validate(
            {
                "chats": chats,
                "sign_at": sign_at,
                "random_seconds": random_seconds,
            }
        )

    def write_config(self, config: SignConfig):
        with open(self.config_file, "w", encoding="utf-8") as fp:
            json.dump(config.to_jsonable(), fp)

    def reconfig(self):
        config = self.ask_for_config()
        self.write_config(config)
        return config

    def load_config(self) -> "SignConfig":
        if not self.config_file.exists():
            config = self.reconfig()
        else:
            with open(self.config_file, "r", encoding="utf-8") as fp:
                config, from_old = SignConfig.load(json.load(fp))
                if from_old:
                    self.write_config(config)
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

    async def login(self, num_of_dialogs=20, print_chat=True):
        app = self.app
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
                if print_chat:
                    print(latest_chats[-1])

            with open(
                self.workdir.joinpath("latest_chats.json"), "w", encoding="utf-8"
            ) as fp:
                json.dump(
                    latest_chats,
                    fp,
                    indent=4,
                    default=Object.default,
                    ensure_ascii=False,
                )

    async def logout(self):
        is_authorized = await self.app.connect()
        if not is_authorized:
            await self.app.storage.delete()
            return
        return await self.app.log_out()

    def get_task_list(self):
        signs = []
        for d in os.listdir(self.signs_dir):
            if self.signs_dir.joinpath(d).is_dir():
                signs.append(d)
        return signs

    def list_(self):
        print("已配置的任务：")
        for d in self.get_task_list():
            print(d)

    async def sign(self, chat_id: int, sign_text: str):
        await self.app.send_message(chat_id, sign_text)

    async def run(
        self, num_of_dialogs=20, only_once: bool = False, force_rerun: bool = False
    ):
        if self.user is None:
            await self.login(num_of_dialogs, print_chat=True)

        config = self.load_config()
        sign_record = self.load_sign_record()
        sign_at = config.sign_at
        while True:
            try:
                async with self.app:
                    now = get_now()
                    logger.info(f"当前时间: {now}")
                    now_date_str = str(now.date())
                    if now_date_str not in sign_record or force_rerun:
                        for chat in config.chats:
                            await self.sign(chat.chat_id, chat.sign_text)
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

    async def run_once(self, num_of_dialogs):
        return await self.run(num_of_dialogs, only_once=True, force_rerun=True)

    async def send_text(self, chat_id: int, text: str):
        if self.user is None:
            await self.login(print_chat=False)
        async with self.app:
            await self.app.send_message(chat_id, text)

    def app_run(self, coroutine=None):
        self.app.run(coroutine)
