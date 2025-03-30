import asyncio
import json
import logging
import os
import pathlib
import random
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from datetime import time as dt_time
from typing import Any, BinaryIO, Optional, Type, TypedDict, TypeVar, Union
from urllib import parse

from croniter import CroniterBadCronError, croniter
from pyrogram import Client as BaseClient
from pyrogram import errors, filters
from pyrogram.enums import ChatMembersFilter, ChatType
from pyrogram.handlers import MessageHandler
from pyrogram.methods.utilities.idle import idle
from pyrogram.session import Session as BaseSession
from pyrogram.storage import MemoryStorage
from pyrogram.types import (
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Object,
    User,
)

from tg_signer.config import (
    BaseJSONConfig,
    MatchConfig,
    MonitorConfig,
    SignChat,
    SignConfig,
)

from .ai_tools import (
    calculate_problem,
    choose_option_by_image,
    get_openai_client,
    get_reply,
)
from .notification.server_chan import sc_send

logger = logging.getLogger("tg-signer")

print_to_user = print

DICE_EMOJIS = ("🎲", "🎯", "🏀", "⚽", "🎳", "🎰")


class Session(BaseSession):
    START_TIMEOUT = 5


class UserInput:
    def __init__(self, index: int = 1):
        self.index = index

    def __call__(self, prompt: str = None):
        r = input(f"{self.index}. {prompt}")
        self.index += 1
        return r


def readable_message(message: Message):
    s = "\nMessage: "
    s += f"\n  text: {message.text or ''}"
    if message.photo:
        s += f"\n  图片: [({message.photo.width}x{message.photo.height}) {message.caption}]"
    if message.reply_markup:
        if isinstance(message.reply_markup, InlineKeyboardMarkup):
            s += "\n  InlineKeyboard: "
            for row in message.reply_markup.inline_keyboard:
                s += "\n   "
                for button in row:
                    s += f"{button.text} | "
    return s


def readable_chat(chat: Chat):
    if chat.type == ChatType.BOT:
        type_ = "BOT"
    elif chat.type == ChatType.GROUP:
        type_ = "群组"
    elif chat.type == ChatType.SUPERGROUP:
        type_ = "超级群组"
    elif chat.type == ChatType.CHANNEL:
        type_ = "频道"
    else:
        type_ = "个人"

    none_or_dash = lambda x: x or "-"  # noqa: E731

    return f"id: {chat.id}, username: {none_or_dash(chat.username)}, title: {none_or_dash(chat.title)}, type: {type_}, name: {none_or_dash(chat.first_name)}"


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
    workdir: Union[str, pathlib.Path] = ".",
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
        self.task_name = task_name or "my_task"
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
        self.user: Optional[User] = None
        self._config = None
        self.context = self.ensure_ctx()

    def ensure_ctx(self):
        return {}

    def app_run(self, coroutine=None):
        if coroutine is not None:
            loop = asyncio.get_event_loop()
            run = loop.run_until_complete
            run(coroutine)
        else:
            self.app.run()

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

    def get_user_dir(self, user: User):
        user_dir = self.workdir / "users" / str(user.id)
        make_dirs(user_dir)
        return user_dir

    @property
    def config_file(self):
        return self.task_dir.joinpath("config.json")

    @property
    def config(self) -> ConfigT:
        return self._config or self.load_config()

    @config.setter
    def config(self, value):
        self._config = value

    def log(self, msg, level: str = "INFO", **kwargs):
        msg = f"{self._account}: {msg}"
        if level.upper() == "INFO":
            logger.info(msg, **kwargs)
        elif level.upper() == "WARNING":
            logger.warning(msg, **kwargs)
        elif level.upper() == "ERROR":
            logger.error(msg, **kwargs)
        elif level.upper() == "CRITICAL":
            logger.critical(msg, **kwargs)
        else:
            logger.debug(msg, **kwargs)

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

    def list_(self):
        print_to_user("已配置的任务：")
        for d in self.get_task_list():
            print_to_user(d)

    def set_me(self, user: User):
        self.user = user
        with open(
            self.get_user_dir(user).joinpath("me.json"), "w", encoding="utf-8"
        ) as fp:
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
                    print_to_user(readable_chat(chat))

            with open(
                self.get_user_dir(me).joinpath("latest_chats.json"),
                "w",
                encoding="utf-8",
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
        self, chat_id: Union[int, str], text: str, delete_after: int = None, **kwargs
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
            self.log(
                f"Message「{text}」 to {chat_id} will be deleted after {delete_after} seconds."
            )
            self.log("Waiting...")
            await asyncio.sleep(delete_after)
            await message.delete()
            self.log(f"Message「{text}」 to {chat_id} deleted!")
        return message

    async def send_dice(
        self,
        chat_id: Union[int, str],
        emoji: str = "🎲",
        delete_after: int = None,
        **kwargs,
    ):
        """
        发送DICE类型消息
        :param chat_id:
        :param emoji: Should be one of "🎲", "🎯", "🏀", "⚽", "🎳", or "🎰".
        :param delete_after:
        :param kwargs:
        :return:
        """
        emoji = emoji.strip()
        if emoji not in DICE_EMOJIS:
            self.log(
                f"Warning, emoji should be one of {', '.join(DICE_EMOJIS)}",
                level="WARNING",
            )
        message = await self.app.send_dice(chat_id, emoji, **kwargs)
        if message and delete_after is not None:
            self.log(
                f"Dice「{emoji}」 to {chat_id} will be deleted after {delete_after} seconds."
            )
            self.log("Waiting...")
            await asyncio.sleep(delete_after)
            await message.delete()
            self.log(f"Dice「{emoji}」 to {chat_id} deleted!")
        return message

    async def search_members(
        self, chat_id: Union[int, str], query: str, admin=False, limit=10
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
        self, chat_id: Union[int, str], query: str = "", admin=False, limit=10
    ):
        async with self.app:
            async for member in self.search_members(chat_id, query, admin, limit):
                print_to_user(
                    User(
                        id=member.user.id,
                        username=member.user.username,
                        first_name=member.user.first_name,
                        last_name=member.user.last_name,
                        is_bot=member.user.is_bot,
                    )
                )

    def export(self):
        with open(self.config_file, "r", encoding="utf-8") as fp:
            data = fp.read()
        return data

    def import_(self, config_str: str):
        with open(self.config_file, "w", encoding="utf-8") as fp:
            fp.write(config_str)

    def ask_one(self):
        raise NotImplementedError


class WaitCounter:
    def __init__(self):
        self.waiting_ids = set()
        self.waiting_counter = Counter()

    def add(self, elm):
        self.waiting_ids.add(elm)
        self.waiting_counter[elm] += 1

    def discard(self, elm):
        self.waiting_ids.discard(elm)
        self.waiting_counter.pop(elm, None)

    def sub(self, elm):
        self.waiting_counter[elm] -= 1
        if self.waiting_counter[elm] <= 0:
            self.discard(elm)

    def clear(self):
        self.waiting_ids.clear()
        self.waiting_counter.clear()

    def __bool__(self):
        return bool(self.waiting_ids)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.waiting_counter}>"


class UserSignerWorkerContext(TypedDict, total=False):
    waiting_counter: WaitCounter
    sign_chats: dict[int, list[SignChat]]


OPENAI_USE_PROMPT = '在运行前请通过环境变量正确设置`OPENAI_API_KEY`, `OPENAI_BASE_URL`。默认模型为"gpt-4o", 可通过环境变量`OPENAI_MODEL`更改。'


class UserSigner(BaseUserWorker):
    _workdir = ".signer"
    _tasks_dir = "signs"
    cfg_cls = SignConfig
    context: UserSignerWorkerContext

    def ensure_ctx(self) -> UserSignerWorkerContext:
        return {"waiting_counter": WaitCounter(), "sign_chats": defaultdict(list)}

    @property
    def sign_record_file(self):
        sign_record_dir = self.task_dir / str(self.user.id)
        make_dirs(sign_record_dir)
        return sign_record_dir / "sign_record.json"

    def _ask_keyboard(self, cfgs: dict[str, Any], input_: UserInput):
        has_keyboard = input_("是否有键盘？(y/N)：")
        text_of_btn_to_click = None
        if has_keyboard.strip().lower() == "y":
            text_of_btn_to_click = input_(
                "键盘中需要点击的按钮文本（无则直接回车）: "
            ).strip()
        cfgs["text_of_btn_to_click"] = text_of_btn_to_click
        return cfgs

    def _ask_choose_option_by_image(self, cfgs: dict[str, Any], input_: UserInput):
        choose_option_by_image_input = input_("是否有识图选择题？(y/N)：")
        choose_option_by_image_ = choose_option_by_image_input.strip().lower() == "y"
        if choose_option_by_image_:
            print_to_user("图片识别将使用大模型回答，请确保大模型支持图片识别。")
        cfgs["choose_option_by_image"] = choose_option_by_image_
        return cfgs

    def _ask_has_calculation_problem(self, cfgs: dict[str, Any], input_: UserInput):
        if cfgs["choose_option_by_image"]:
            print_to_user("当前'识图选择题'和'简单计算题'互斥，不同时支持。")
            return cfgs
        has_calculation_problem_input = input_("是否有简单计算题？(y/N)：")
        has_calculation_problem = has_calculation_problem_input.strip().lower() == "y"
        if has_calculation_problem:
            print_to_user("计算题将使用大模型回答。")
        cfgs["has_calculation_problem"] = has_calculation_problem
        return cfgs

    def ask_one(self) -> SignChat:
        input_ = UserInput()
        chat_id = int(input_("Chat ID（登录时最近对话输出中的ID）: "))
        sign_text = input_("签到文本（如 /sign）: ") or "/sign"
        sign_text = sign_text.strip()
        as_dice = False
        if sign_text in DICE_EMOJIS:
            as_dice_str = input_("是否以骰子类的emoji（如 🎲, 🎯）发送？(y/N)：")
            as_dice = as_dice_str.strip().lower() == "y"
        delete_after = (
            input_(
                "等待N秒后删除签到消息（发送消息后等待进行删除, '0'表示立即删除, 不需要删除直接回车）, N: "
            )
            or None
        )
        if delete_after:
            delete_after = int(delete_after)
        cfgs = {
            "chat_id": chat_id,
            "sign_text": sign_text,
            "delete_after": delete_after,
            "as_dice": as_dice,
        }
        cfgs.update(self._ask_keyboard(cfgs, input_))
        cfgs.update(self._ask_choose_option_by_image(cfgs, input_))
        cfgs.update(self._ask_has_calculation_problem(cfgs, input_))
        if cfgs["choose_option_by_image"] or cfgs["has_calculation_problem"]:
            print_to_user(OPENAI_USE_PROMPT)
        return SignChat.model_validate(cfgs)

    def ask_for_config(self) -> "SignConfig":
        chats = []
        i = 1
        print_to_user(f"开始配置任务<{self.task_name}>")
        while True:
            print_to_user(f"第{i}个签到")
            try:
                chats.append(self.ask_one())
            except Exception as e:
                print_to_user(e)
                print_to_user("配置失败")
                i -= 1
            continue_ = input("继续配置签到？(y/N)：")
            if continue_.strip().lower() != "y":
                break
            i += 1
        sign_at_prompt = (
            "每日签到时间（time或crontab表达式，如'06:00:00'或'0 6 * * *'）: "
        )
        sign_at_str = input(sign_at_prompt) or "06:00:00"
        while not (sign_at := self._validate_sign_at(sign_at_str)):
            print_to_user("请输入正确的时间格式")
            sign_at_str = input(sign_at_prompt) or "06:00:00"

        random_seconds_str = input("签到时间误差随机秒数（默认为0）: ") or "0"
        random_seconds = int(float(random_seconds_str))
        config = SignConfig.model_validate(
            {
                "chats": chats,
                "sign_at": sign_at,
                "random_seconds": random_seconds,
            }
        )
        return config

    @classmethod
    def _validate_sign_at(cls, sign_at_str: str) -> Optional[str]:
        sign_at_str = sign_at_str.replace("：", ":").strip()

        try:
            sign_at = dt_time.fromisoformat(sign_at_str)
            crontab_expr = cls._time_to_crontab(sign_at)
        except ValueError:
            try:
                croniter(sign_at_str)
                crontab_expr = sign_at_str
            except CroniterBadCronError:
                return None
        return crontab_expr

    @staticmethod
    def _time_to_crontab(sign_at: time) -> str:
        return f"{sign_at.minute} {sign_at.hour} * * *"

    def load_sign_record(self):
        sign_record = {}
        if not self.sign_record_file.is_file():
            with open(self.sign_record_file, "w", encoding="utf-8") as fp:
                json.dump(sign_record, fp)
        else:
            with open(self.sign_record_file, "r", encoding="utf-8") as fp:
                sign_record = json.load(fp)
        return sign_record

    async def sign(
        self,
        chat: SignChat,
    ):
        if chat.as_dice:
            return await self.send_dice(chat.chat_id, chat.sign_text, chat.delete_after)
        return await self.send_message(chat.chat_id, chat.sign_text, chat.delete_after)

    async def run(
        self, num_of_dialogs=20, only_once: bool = False, force_rerun: bool = False
    ):
        if self.user is None:
            await self.login(num_of_dialogs, print_chat=True)

        config = self.load_config(self.cfg_cls)
        sign_record = self.load_sign_record()
        chat_ids = [c.chat_id for c in config.chats]
        while True:
            self.log(f"为以下Chat添加消息回调处理函数：{chat_ids}")
            self.app.add_handler(
                MessageHandler(self.on_message, filters.chat(chat_ids))
            )
            try:
                async with self.app:
                    now = get_now()
                    self.log(f"当前时间: {now}")
                    now_date_str = str(now.date())
                    self.context["waiting_counter"].clear()
                    if now_date_str not in sign_record or force_rerun:
                        for chat in config.chats:
                            self.context["sign_chats"][chat.chat_id].append(chat)
                            self.log(f"发送消息至「{chat.chat_id}」")
                            try:
                                await self.sign(chat)
                            except errors.BadRequest as e:
                                self.log(f"发送消息失败：{e}")
                                continue

                            if chat.text_of_btn_to_click:
                                self.context["waiting_counter"].add(chat.chat_id)
                            if chat.has_calculation_problem:
                                self.context["waiting_counter"].add(chat.chat_id)
                            if chat.choose_option_by_image:
                                self.context["waiting_counter"].add(chat.chat_id)
                            await asyncio.sleep(0.5)
                        sign_record[now_date_str] = now.isoformat()
                        with open(self.sign_record_file, "w", encoding="utf-8") as fp:
                            json.dump(sign_record, fp)

                        wait_seconds = 60
                        self.log(
                            rf"最多等待{wait_seconds}秒，用于响应可能的键盘点击\识图选择题\计算题..."
                        )
                        _start = time.perf_counter()
                        while (time.perf_counter() - _start) <= wait_seconds and bool(
                            self.context["waiting_counter"]
                        ):
                            await asyncio.sleep(1)
                        self.log("Done")

                    else:
                        print_to_user(
                            f"当前任务今日已签到，签到时间: {sign_record[now_date_str]}"
                        )

            except (OSError, errors.Unauthorized) as e:
                logger.exception(e)
                await asyncio.sleep(30)
                continue

            if only_once:
                break
            cron_it = croniter(self._validate_sign_at(config.sign_at), now)
            next_run: datetime = cron_it.next(datetime) + timedelta(
                seconds=random.randint(0, int(config.random_seconds))
            )
            self.log(f"下次运行时间: {next_run}")
            await asyncio.sleep((next_run - now).total_seconds())

    async def run_once(self, num_of_dialogs):
        return await self.run(num_of_dialogs, only_once=True, force_rerun=True)

    async def send_text(
        self, chat_id: int, text: str, delete_after: int = None, **kwargs
    ):
        if self.user is None:
            await self.login(print_chat=False)
        async with self.app:
            await self.send_message(chat_id, text, delete_after, **kwargs)

    async def send_dice_cli(
        self,
        chat_id: Union[str, int],
        emoji: str = "🎲",
        delete_after: int = None,
        **kwargs,
    ):
        if self.user is None:
            await self.login(print_chat=False)
        async with self.app:
            await self.send_dice(chat_id, emoji, delete_after, **kwargs)

    async def on_message(self, client, message: Message):
        try:
            await self._on_message(client, message)
        except Exception as e:
            logger.exception(e)

    async def _on_message(self, client: Client, message: Message):
        self.log(
            f"收到来自「{message.from_user.username or message.from_user.id}」的消息: {readable_message(message)}"
        )
        chats = self.context["sign_chats"].get(message.chat.id)
        if not chats:
            self.log("忽略意料之外的聊天", level="WARNING")
            return
        # 依次尝试匹配。同一个chat可能配置多个签到，但是没办法保证对方的回复按序到达
        for chat in chats:
            await self.handle_once(chat, client, message)

    async def handle_once(
        self, chat: SignChat, client: Client, message: Message
    ) -> Optional[bool]:
        if not chat.need_response:
            self.log("忽略，未显式配置为需要响应")
            return False
        text_of_btn_to_click = chat.text_of_btn_to_click
        if reply_markup := message.reply_markup:
            # 键盘
            if isinstance(reply_markup, InlineKeyboardMarkup):
                flat_buttons = (b for row in reply_markup.inline_keyboard for b in row)
                option_to_btn: dict[str, InlineKeyboardButton] = {}
                # 未配置需要点击的按钮
                if not text_of_btn_to_click:
                    option_to_btn = {btn.text: btn for btn in flat_buttons if btn.text}
                else:
                    # 遍历button并根据配置的按钮文本匹配
                    for btn in flat_buttons:
                        option_to_btn[btn.text] = btn
                        if text_of_btn_to_click in btn.text:
                            self.log(f"点击按钮: {btn.text}")
                            await self.request_callback_answer(
                                client, message.chat.id, message.id, btn.callback_data
                            )
                            self.context["waiting_counter"].sub(message.chat.id)
                            return True
                if message.photo is not None and chat.choose_option_by_image:
                    self.log("检测到图片，尝试调用大模型进行图片")
                    ai_client = get_openai_client()
                    if not ai_client:
                        self.log(
                            "未配置OpenAI API Key，无法使用AI服务", level="WARNING"
                        )
                        return False
                    image_buffer: BinaryIO = await client.download_media(
                        message.photo.file_id, in_memory=True
                    )
                    image_buffer.seek(0)
                    image_bytes = image_buffer.read()
                    options = list(option_to_btn)
                    result_index = await choose_option_by_image(
                        image_bytes,
                        "选择正确的选项",
                        list(enumerate(options)),
                        client=ai_client,
                    )
                    result = options[result_index]
                    self.log(f"选择结果为: {result}")
                    target_btn = option_to_btn.get(result.strip())
                    if not target_btn:
                        self.log("未找到匹配的按钮", level="WARNING")
                        return False
                    await self.request_callback_answer(
                        client, message.chat.id, message.id, target_btn.callback_data
                    )
                    self.context["waiting_counter"].sub(message.chat.id)
                    return True
            else:
                self.log(f"忽略类型: {type(reply_markup)}", level="WARNING")

        if chat.has_calculation_problem and message.text:
            self.log("检测到文本回复，尝试调用大模型进行计算题回答")
            ai_client = get_openai_client()
            if not ai_client:
                self.log("未配置OpenAI API Key，无法使用AI服务", level="WARNING")
                return False
            self.log(f"问题: \n{message.text}")
            answer = await calculate_problem(message.text, client=ai_client)
            self.log(f"回答为: {answer}")
            await self.send_message(message.chat.id, answer)
            self.context["waiting_counter"].sub(message.chat.id)

    async def request_callback_answer(
        self,
        client: Client,
        chat_id: Union[int, str],
        message_id: int,
        callback_data: Union[str, bytes],
        **kwargs,
    ):
        try:
            await client.request_callback_answer(
                chat_id, message_id, callback_data=callback_data, **kwargs
            )
            self.log("点击完成")
        except (errors.BadRequest, TimeoutError) as e:
            self.log(e, level="ERROR")

    async def schedule_messages(
        self,
        chat_id: Union[int, str],
        text: str,
        crontab: str = None,
        next_times: int = 1,
        random_seconds: int = 0,
    ):
        now = get_now()
        it = croniter(crontab, start_time=now)
        if self.user is None:
            await self.login(print_chat=False)
        results = []
        async with self.app:
            for n in range(next_times):
                next_dt: datetime = it.next(ret_type=datetime) + timedelta(
                    seconds=random.randint(0, random_seconds)
                )
                results.append({"at": next_dt.isoformat(), "text": text})
                await self.app.send_message(
                    chat_id,
                    text,
                    schedule_date=next_dt,
                )
                await asyncio.sleep(0.1)
                print_to_user(f"已配置次数：{n + 1}")
        self.log(f"已配置定时发送消息，次数{next_times}")
        return results

    async def get_schedule_messages(self, chat_id):
        if self.user is None:
            await self.login(print_chat=False)
        async with self.app:
            messages = await self.app.get_scheduled_messages(chat_id)
            for message in messages:
                print_to_user(f"{message.date}: {message.text}")


class UserMonitor(BaseUserWorker):
    _workdir = ".monitor"
    _tasks_dir = "monitors"
    cfg_cls = MonitorConfig
    config: MonitorConfig

    def ask_one(self):
        input_ = UserInput()
        chat_id = (input_("Chat ID（登录时最近对话输出中的ID）: ")).strip()
        if not chat_id.startswith("@"):
            chat_id = int(chat_id)
        rules = ["exact", "contains", "regex", "all"]
        while rule := input_(f"匹配规则({', '.join(rules)}): ") or "exact":
            if rule in rules:
                break
            print_to_user("不存在的规则, 请重新输入!")
        rule_value = None
        if rule != "all":
            while not (rule_value := input_("规则值（不可为空）: ")):
                print_to_user("不可为空！")
                continue
        from_user_ids = (
            input_(
                "只匹配来自特定用户ID的消息（多个用逗号隔开, 匹配所有用户直接回车）: "
            )
            or None
        )
        if from_user_ids:
            from_user_ids = [
                i if i.startswith("@") else int(i) for i in from_user_ids.split(",")
            ]
        default_send_text = input_("默认发送文本: ") or None
        ai_reply = False
        ai_prompt = None
        use_ai_reply = input_("是否使用AI进行回复(y/N): ") or "n"
        if use_ai_reply.lower() == "y":
            ai_reply = True
            while not (ai_prompt := input_("输入你的提示词（作为`system prompt`）: ")):
                print_to_user("不可为空！")
                continue
            print_to_user(OPENAI_USE_PROMPT)

        send_text_search_regex = None
        if not ai_reply:
            send_text_search_regex = (
                input_("从消息中提取发送文本的正则表达式（不需要则直接回车）: ") or None
            )

        delete_after = (
            input_(
                "等待N秒后删除签到消息（发送消息后等待进行删除, '0'表示立即删除, 不需要删除直接回车）, N: "
            )
            or None
        )
        if delete_after:
            delete_after = int(delete_after)
        forward_to_chat_id = (input_("转发消息到该聊天ID，默认为消息来源：")).strip()
        if forward_to_chat_id and not forward_to_chat_id.startswith("@"):
            forward_to_chat_id = int(forward_to_chat_id)
        push_via_server_chan = (
            input_("是否通过Server酱推送消息(y/N): ") or "n"
        ).lower() == "y"
        server_chan_send_key = (
            input_("Server酱的SendKey（不填将从环境变量`SERVER_CHAN_SEND_KEY`读取: ")
            or None
        )
        return MatchConfig.model_validate(
            {
                "chat_id": chat_id,
                "rule": rule,
                "rule_value": rule_value,
                "from_user_ids": from_user_ids,
                "default_send_text": default_send_text,
                "ai_reply": ai_reply,
                "ai_prompt": ai_prompt,
                "send_text_search_regex": send_text_search_regex,
                "delete_after": delete_after,
                "forward_to_chat_id": forward_to_chat_id,
                "push_via_server_chan": push_via_server_chan,
                "server_chan_send_key": server_chan_send_key,
            }
        )

    def ask_for_config(self) -> "MonitorConfig":
        i = 1
        print_to_user(f"开始配置任务<{self.task_name}>")
        print_to_user(
            "聊天chat id和用户user id均同时支持整数id和字符串username, username必须以@开头，如@neo"
        )
        match_cfgs = []
        while True:
            print_to_user(f"\n配置第{i}个监控项")
            try:
                match_cfgs.append(self.ask_one())
            except Exception as e:
                print_to_user(e)
                print_to_user("配置失败")
                i -= 1
            continue_ = input("继续配置？(y/N)：")
            if continue_.strip().lower() != "y":
                break
            i += 1
        return MonitorConfig(match_cfgs=match_cfgs)

    async def on_message(self, client, message: Message):
        for match_cfg in self.config.match_cfgs:
            if not match_cfg.match(message):
                continue
            self.log(f"匹配到监控项：{match_cfg}")
            try:
                send_text = await self.get_send_text(match_cfg, message)
                if not send_text:
                    self.log("发送内容为空", level="WARNING")
                else:
                    forward_to_chat_id = match_cfg.forward_to_chat_id or message.chat.id
                    self.log(f"发送文本：{send_text}至{forward_to_chat_id}")
                    await self.send_message(
                        forward_to_chat_id,
                        send_text,
                        delete_after=match_cfg.delete_after,
                    )

                if match_cfg.push_via_server_chan:
                    server_chan_send_key = (
                        match_cfg.server_chan_send_key
                        or os.environ.get("SERVER_CHAN_SEND_KEY")
                    )
                    if not server_chan_send_key:
                        self.log("未配置Server酱的SendKey", level="WARNING")
                    else:
                        await sc_send(
                            server_chan_send_key,
                            f"匹配到监控项：{match_cfg.chat_id}",
                            f"消息内容为:\n\n{message.text}",
                        )
            except IndexError as e:
                logger.exception(e)

    async def get_send_text(self, match_cfg: MatchConfig, message: Message) -> str:
        send_text = match_cfg.get_send_text(message.text)
        if match_cfg.ai_reply and match_cfg.ai_prompt:
            ai_client = get_openai_client()
            if not ai_client:
                self.log("未配置OpenAI API Key，无法使用AI服务", level="WARNING")
                return send_text
            send_text = await get_reply(
                match_cfg.ai_prompt, message.text, client=ai_client
            )
        return send_text

    async def run(self, num_of_dialogs=20):
        if self.user is None:
            await self.login(num_of_dialogs, print_chat=True)

        cfg = self.load_config(self.cfg_cls)
        self.app.add_handler(
            MessageHandler(self.on_message, filters.text & filters.chat(cfg.chat_ids)),
        )
        async with self.app:
            self.log("开始监控...")
            await idle()
