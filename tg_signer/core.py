import asyncio
import json
import logging
import os
import pathlib
import random
from datetime import datetime, time, timedelta, timezone
from typing import Type, TypeVar, Union
from urllib import parse

from pyrogram import Client as BaseClient, errors, filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.handlers import MessageHandler
from pyrogram.methods.utilities.idle import idle
from pyrogram.storage import MemoryStorage
from pyrogram.types import Message, Object, User

from tg_signer.config import BaseJSONConfig, MatchConfig, MonitorConfig, SignConfig

logger = logging.getLogger("tg-signer")


class Client(BaseClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.in_memory and not self.session_string:
            self.load_session_string()
            self.storage = MemoryStorage(self.name, self.session_string)

    async def __aenter__(self):
        try:
            return await self.start()
        except ConnectionError:
            pass

    @property
    def session_string_file(self):
        return self.workdir / (self.name + ".session_string")

    async def save_session_string(self):
        with open(self.session_string_file, "w") as fp:
            fp.write(await self.export_session_string())

    def load_session_string(self):
        logger.info("Loading session_string from local file.")
        if self.session_string_file.is_file():
            with open(self.session_string_file, "r") as fp:
                self.session_string = fp.read()
                logger.info("The session_string has been loaded.")
        return self.session_string

    async def log_out(
        self,
    ):
        await super().log_out()
        if self.session_string_file.is_file():
            os.remove(self.session_string_file)


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


def get_client(
    name: str = "my_account",
    proxy: dict = None,
    workdir: str | pathlib.Path = ".",
    session_string: str = None,
    in_memory: bool = False,
    **kwargs,
):
    proxy = proxy or get_proxy()
    api_id, api_hash = get_api_config()
    return Client(
        name,
        api_id,
        api_hash,
        proxy=proxy,
        workdir=workdir,
        session_string=session_string,
        in_memory=in_memory,
        **kwargs,
    )


def get_now():
    return datetime.now(tz=timezone(timedelta(hours=8)))


def make_dirs(path: pathlib.Path, exist_ok=True):
    path = pathlib.Path(path)
    if not path.is_dir():
        os.makedirs(path, exist_ok=exist_ok)
    return path


ConfigT = TypeVar("ConfigT", bound=BaseJSONConfig)


class BaseUserWorker:
    _workdir = "."
    _tasks_dir = "tasks"
    cfg_cls: Type[ConfigT] = BaseJSONConfig

    def __init__(
        self,
        task_name: str = None,
        session_dir: str = ".",
        account: str = "my_account",
        proxy=None,
        workdir=None,
        session_string: str = None,
        in_memory: bool = False,
    ):
        self.task_name = task_name
        self._session_dir = pathlib.Path(session_dir)
        self._account = account
        self._proxy = proxy
        if workdir:
            self._workdir = pathlib.Path(workdir)
        self.app = get_client(
            account,
            proxy,
            workdir=self._session_dir,
            session_string=session_string,
            in_memory=in_memory,
        )
        self.user = None
        self._config = None

    def app_run(self, coroutine=None):
        self.app.run(coroutine)

    @property
    def workdir(self) -> pathlib.Path:
        workdir = self._workdir
        make_dirs(workdir)
        return pathlib.Path(workdir)

    @property
    def tasks_dir(self):
        tasks_dir = self.workdir / self._tasks_dir
        make_dirs(tasks_dir)
        return pathlib.Path(tasks_dir)

    @property
    def task_dir(self):
        task_dir = self.tasks_dir / self.task_name
        make_dirs(task_dir)
        return task_dir

    @property
    def config_file(self):
        return self.task_dir.joinpath("config.json")

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, value):
        self._config = value

    def ask_for_config(self):
        raise NotImplementedError

    def write_config(self, config: BaseJSONConfig):
        with open(self.config_file, "w", encoding="utf-8") as fp:
            json.dump(config.to_jsonable(), fp, ensure_ascii=False)

    def reconfig(self):
        config = self.ask_for_config()
        self.write_config(config)
        return config

    def load_config(self, cfg_cls: Type[ConfigT] = None) -> ConfigT:
        cfg_cls = cfg_cls or self.cfg_cls
        if not self.config_file.exists():
            config = self.reconfig()
        else:
            with open(self.config_file, "r", encoding="utf-8") as fp:
                config, from_old = cfg_cls.load(json.load(fp))
                if from_old:
                    self.write_config(config)
        self.config = config
        return config

    def get_task_list(self):
        signs = []
        for d in os.listdir(self.tasks_dir):
            if self.tasks_dir.joinpath(d).is_dir():
                signs.append(d)
        return signs

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
            await self.app.save_session_string()

    async def logout(self):
        is_authorized = await self.app.connect()
        if not is_authorized:
            await self.app.storage.delete()
            return
        return await self.app.log_out()

    async def send_message(
        self, chat_id: int | str, text: str, delete_after: int = None, **kwargs
    ):
        """
        发送文本消息
        :param chat_id:
        :param text:
        :param delete_after: 秒, 发送消息后进行删除，``None`` 表示不删除, ``0`` 表示立即删除.
        :param kwargs:
        :return:
        """
        message = await self.app.send_message(chat_id, text, **kwargs)
        if delete_after is not None:
            logger.info(
                f"Message「{text}」 to {chat_id} will be deleted after {delete_after} seconds."
            )
            logger.info("Waiting...")
            await asyncio.sleep(delete_after)
            await message.delete()
            logger.info(f"Message「{text}」 to {chat_id} deleted!")
        return message

    async def search_members(
        self, chat_id: Union[int | str], query: str, admin=False, limit=10
    ):
        filter_ = ChatMembersFilter.SEARCH
        if admin:
            filter_ = ChatMembersFilter.ADMINISTRATORS
            query = ""
        async for member in self.app.get_chat_members(
            chat_id, query, limit=limit, filter=filter_
        ):
            yield member

    async def list_members(
        self, chat_id: Union[int | str], query: str = "", admin=False, limit=10
    ):
        async with self.app:
            async for member in self.search_members(chat_id, query, admin, limit):
                print(
                    User(
                        id=member.user.id,
                        username=member.user.username,
                        first_name=member.user.first_name,
                        last_name=member.user.last_name,
                        is_bot=member.user.is_bot,
                    )
                )


class UserSigner(BaseUserWorker):
    _workdir = ".signer"
    _tasks_dir = "signs"
    cfg_cls = SignConfig

    @property
    def sign_record_file(self):
        return self.task_dir.joinpath("sign_record.json")

    def ask_for_config(self) -> "SignConfig":
        chats = []
        i = 1
        print(f"开始配置任务<{self.task_name}>")
        while True:
            print(f"第{i}个签到")
            chat_id = int(input("1. Chat ID（登录时最近对话输出中的ID）: "))
            sign_text = input("2. 签到文本（如 /sign）: ") or "/sign"
            delete_after = (
                input(
                    "3. 等待N秒后删除签到消息（发送消息后等待进行删除, '0'表示立即删除, 不需要删除直接回车）, N: "
                )
                or None
            )
            if delete_after:
                delete_after = int(delete_after)
            chats.append(
                {
                    "chat_id": chat_id,
                    "sign_text": sign_text,
                    "delete_after": delete_after,
                }
            )
            continue_ = input("继续配置签到？(y/N)：")
            if continue_.strip().lower() != "y":
                break
            i += 1
        sign_at_str = input("4. 每日签到时间（如 06:00:00）: ") or "06:00:00"
        sign_at_str = sign_at_str.replace("：", ":").strip()
        sign_at = time.fromisoformat(sign_at_str)
        random_seconds_str = input("5. 签到时间误差随机秒数（默认为0）: ") or "0"
        random_seconds = int(float(random_seconds_str))
        config = SignConfig.model_validate(
            {
                "chats": chats,
                "sign_at": sign_at,
                "random_seconds": random_seconds,
            }
        )
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

    def list_(self):
        print("已配置的任务：")
        for d in self.get_task_list():
            print(d)

    async def sign(self, chat_id: int, sign_text: str, delete_after: int = None):
        await self.send_message(chat_id, sign_text, delete_after)

    async def run(
        self, num_of_dialogs=20, only_once: bool = False, force_rerun: bool = False
    ):
        if self.user is None:
            await self.login(num_of_dialogs, print_chat=True)

        config = self.load_config(self.cfg_cls)
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
                            await self.sign(
                                chat.chat_id, chat.sign_text, chat.delete_after
                            )
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

    async def send_text(self, chat_id: int, text: str, delete_after: int = None):
        if self.user is None:
            await self.login(print_chat=False)
        async with self.app:
            await self.send_message(chat_id, text, delete_after)


class UserMonitor(BaseUserWorker):
    _workdir = ".monitor"
    _tasks_dir = "monitors"
    cfg_cls = MonitorConfig
    config: MonitorConfig

    def ask_for_config(self) -> "MonitorConfig":
        i = 1
        print(f"开始配置任务<{self.task_name}>")
        print(
            "聊天chat id和用户user id均同时支持整数id和字符串username, username必须以@开头，如@neo"
        )
        match_cfgs = []
        while True:
            print(f"\n配置第{i}个监控项")
            chat_id = (input("1. Chat ID（登录时最近对话输出中的ID）: ")).strip()
            if not chat_id.startswith("@"):
                chat_id = int(chat_id)
            rules = ["exact", "contains", "regex"]
            while (
                rule := input("2. 匹配规则('exact', 'contains', 'regex'): ") or "exact"
            ):
                if rule in rules:
                    break
                print("不存在的规则, 请重新输入!")
            while not (rule_value := input("3. 规则值（不可为空）: ")):
                continue
            from_user_ids = (
                input(
                    "4. 只匹配来自特定用户ID的消息（多个用逗号隔开, 匹配所有用户直接回车）: "
                )
                or None
            )
            if from_user_ids:
                from_user_ids = [
                    i if i.startswith("@") else int(i) for i in from_user_ids.split(",")
                ]
            default_send_text = input("5. 默认发送文本: ") or None
            while not (
                send_text_search_regex := input("6. 从消息中提取发送文本的正则表达式: ")
                or None
            ):
                if default_send_text:
                    break
                print("「默认发送文本」为空时必须填写提取发送文本的正则表达式")
                continue

            delete_after = (
                input(
                    "7. 等待N秒后删除签到消息（发送消息后等待进行删除, '0'表示立即删除, 不需要删除直接回车）, N: "
                )
                or None
            )
            if delete_after:
                delete_after = int(delete_after)
            match_cfg = MatchConfig.model_validate(
                dict(
                    chat_id=chat_id,
                    rule=rule,
                    rule_value=rule_value,
                    from_user_ids=from_user_ids,
                    default_send_text=default_send_text,
                    send_text_search_regex=send_text_search_regex,
                    delete_after=delete_after,
                )
            )
            match_cfgs.append(match_cfg)
            continue_ = input("继续配置？(y/N)：")
            if continue_.strip().lower() != "y":
                break
            i += 1
        return MonitorConfig(match_cfgs=match_cfgs)

    async def on_message(self, client, message: Message):
        chat_id = message.chat.id
        for match_cfg in self.config.match_cfgs:
            if not match_cfg.match(message):
                continue
            logger.info(f"匹配到监控项：{match_cfg}")
            try:
                send_text = match_cfg.get_send_text(message.text)
                logger.info(f"发送文本：{send_text}")
                await self.send_message(
                    chat_id, send_text, delete_after=match_cfg.delete_after
                )
            except IndexError as e:
                logger.exception(e)

    async def run(self, num_of_dialogs=20):
        if self.user is None:
            await self.login(num_of_dialogs, print_chat=True)

        cfg = self.load_config(self.cfg_cls)
        self.app.add_handler(
            MessageHandler(self.on_message, filters.text & filters.chat(cfg.chat_ids)),
        )
        async with self.app:
            logger.info("开始监控...")
            await idle()

    def list_(self):
        print("已配置的任务：")
        for d in self.get_task_list():
            print(d)
