import asyncio
import logging
from typing import Optional

import click
from click import Context, HelpFormatter

from tg_signer.core import UserSigner, get_proxy


class AliasedGroup(click.Group):
    _aliases = {"run_once": "run-once", "send_text": "send-text"}

    def __init__(self, name, aliases: dict[str, str] = None, *args, **kwargs):
        self.aliases = self._aliases.copy()
        if aliases:
            self.aliases.update(aliases)
        super().__init__(name, *args, **kwargs)

    def get_command(self, ctx, cmd_name):
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd
        if cmd_name in self.aliases:
            cmd_name = self.aliases[cmd_name]
            return super().get_command(ctx, cmd_name)

    def resolve_command(self, ctx, args):
        # always return the full command name
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args

    def format_help_text(self, ctx: Context, formatter: HelpFormatter) -> None:
        super().format_help_text(ctx, formatter)
        formatter.write_paragraph()
        formatter.write_heading("子命令别名")

        with formatter.indentation():
            for k, v in self.aliases.items():
                formatter.write_text(f"{k} -> {v}")


def get_signer(
    task_name, ctx_obj: dict, loop: Optional[asyncio.AbstractEventLoop] = None
):
    signer = UserSigner(
        task_name=task_name,
        account=ctx_obj["account"],
        proxy=ctx_obj["proxy"],
        session_dir=ctx_obj["session_dir"],
        workdir=ctx_obj["workdir"],
        session_string=ctx_obj["session_string"],
        in_memory=ctx_obj["in_memory"],
        loop=loop,
    )
    return signer


@click.group(name="tg-signer", help="使用<子命令> --help查看使用说明", cls=AliasedGroup)
@click.option(
    "--log-level",
    "-l",
    "log_level",
    default="info",
    show_default=True,
    type=click.Choice(["debug", "info", "warn", "error"], case_sensitive=False),
    help="日志等级, `debug`, `info`, `warn`, `error`",
)
@click.option(
    "--log-file",
    "log_file",
    default="tg-signer.log",
    show_default=True,
    type=click.Path(),
    help="日志文件路径, 可以是相对路径",
)
@click.option(
    "--proxy",
    "-p",
    "proxy",
    default=None,
    show_default=True,
    show_envvar=True,
    envvar="TG_PROXY",
    help="代理地址, 例如: socks5://127.0.0.1:1080, 会覆盖环境变量`TG_PROXY`的值",
)
@click.option(
    "--session_dir",
    "session_dir",
    default=".",
    show_default=True,
    type=click.Path(),
    help="存储TG Sessions的目录, 可以是相对路径",
)
@click.option(
    "--account",
    "-a",
    "account",
    default="my_account",
    show_default=True,
    show_envvar=True,
    envvar="TG_ACCOUNT",
    help="自定义账号名称，对应session文件名为<account>.session",
)
@click.option(
    "--workdir",
    "-w",
    "workdir",
    default=".signer",
    show_default=True,
    type=click.Path(),
    help="tg-signer工作目录，用于存储配置和签到记录等",
)
@click.option(
    "--session-string",
    "session_string",
    default=None,
    show_default=True,
    show_envvar=True,
    envvar="TG_SESSION_STRING",
    help="Telegram Session String, 会覆盖环境变量`TG_SESSION_STRING`的值",
)
@click.option(
    "--in-memory",
    "in_memory",
    default=False,
    is_flag=True,
    help="是否将session存储在内存中，默认为False，存储在文件",
)
@click.pass_context
def tg_signer(
    ctx: click.Context,
    log_level: str,
    log_file: str,
    proxy: str,
    session_dir: str,
    account: str,
    workdir: str,
    session_string: str,
    in_memory: bool,
):
    from tg_signer.logger import configure_logger

    logger = configure_logger(log_level, log_file)
    ctx.ensure_object(dict)
    proxy = get_proxy(proxy)
    if ctx.invoked_subcommand in [
        "login",
        "run",
        "run-once",
        "send-text",
        "logout",
    ]:
        if proxy:
            logger.info(
                "Using proxy: %s"
                % f"{proxy['scheme']}://{proxy['hostname']}:{proxy['port']}"
            )
        logger.info(f"Using account: {account}")
    ctx.obj["proxy"] = proxy
    ctx.obj["session_dir"] = session_dir
    ctx.obj["account"] = account
    ctx.obj["workdir"] = workdir
    ctx.obj["session_string"] = session_string
    ctx.obj["in_memory"] = in_memory


@tg_signer.command(help="Show version")
def version():
    from tg_signer import __version__

    s = f"tg-signer {__version__}"
    click.echo(s)


@tg_signer.command(name="list", help="列出已有配置")
@click.pass_obj
def list_(obj):
    return UserSigner(workdir=obj["workdir"]).list_()


@tg_signer.command(help="登录账号（用于获取session）")
@click.option(
    "--num-of-dialogs",
    "-n",
    default=50,
    show_default=True,
    type=int,
    help="获取最近N个对话, 请确保想要签到的对话在最近N个对话内",
)
@click.pass_obj
def login(obj, num_of_dialogs):
    signer = get_signer(None, obj)
    signer.app_run(signer.login(num_of_dialogs))


@tg_signer.command(help="登出账号并删除session文件")
@click.pass_obj
def logout(obj):
    signer = get_signer(None, obj)
    signer.app_run(signer.logout())


@tg_signer.command(help="根据任务配置运行签到")
@click.argument("task_names", nargs=-1)
@click.option(
    "--num-of-dialogs",
    "-n",
    default=50,
    show_default=True,
    type=int,
    help="获取最近N个对话, 请确保想要签到的对话在最近N个对话内",
)
@click.pass_obj
def run(obj, task_names, num_of_dialogs):
    if len(task_names) < 1:
        raise click.UsageError("At least one task name is required")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    coros = []
    for task_name in task_names:
        signer = get_signer(task_name, obj, loop=loop)
        coros.append(signer.run(num_of_dialogs))
    loop.run_until_complete(asyncio.gather(*coros))


@tg_signer.command(help="运行一次签到任务，即使该签到任务今日已执行过")
@click.argument("task_name", default="my_sign")
@click.option(
    "--num-of-dialogs",
    "-n",
    "num_of_dialogs",
    default=50,
    show_default=True,
    type=int,
    help="获取最近N个对话, 请确保想要签到的对话在最近N个对话内",
)
@click.pass_obj
def run_once(obj, task_name, num_of_dialogs):
    signer = get_signer(task_name, obj)
    signer.app_run(signer.run_once(num_of_dialogs))


@tg_signer.command(help='发送一次文本消息, 请确保当前会话已经"见过"该`chat_id`')
@click.argument(
    "chat_id",
    type=int,
)
@click.argument("text")
@click.option(
    "--delete-after",
    "delete_after",
    type=int,
    required=False,
    help="秒, 发送消息后进行删除, 默认不删除, '0'表示立即删除.",
)
@click.pass_obj
def send_text(obj, chat_id, text, delete_after=None):
    singer = get_signer(None, obj)
    click.echo("将发送单次消息")
    singer.app_run(singer.send_text(chat_id, text, delete_after))


@tg_signer.command(
    help="发送一次DICE消息, 请确保当前会话已经\"见过\"该`chat_id`。\n注意，`emoji`应该是'🎲', '🎯', '🏀', '⚽', '🎳'或'🎰'之一"
)
@click.argument(
    "chat_id",
    type=int,
)
@click.argument("emoji")
@click.option(
    "--delete-after",
    "delete_after",
    type=int,
    required=False,
    help="秒, 发送消息后进行删除, 默认不删除, '0'表示立即删除.",
)
@click.pass_obj
def send_dice(obj, chat_id, emoji, delete_after=None):
    singer = get_signer(None, obj)
    click.echo("将发送单次DICE消息")
    singer.app_run(singer.send_dice_cli(chat_id, emoji, delete_after))


@tg_signer.command(help="重新配置")
@click.argument("task_name", nargs=1, default="my_sign")
@click.pass_obj
def reconfig(obj, task_name):
    signer = UserSigner(task_name=task_name, workdir=obj["workdir"])
    return signer.reconfig()


@tg_signer.command(help="查询聊天（群或频道）的成员, 频道需要管理员权限")
@click.option(
    "--chat_id",
    "chat_id",
    required=True,
    help="整数id或字符串username, username须以@开头",
)
@click.option("--admin", "admin", default=False, is_flag=True, help="只列出管理员")
@click.argument("query", nargs=1, default="")
@click.option(
    "--limit",
    "-l",
    "limit",
    default=10,
    type=int,
)
@click.pass_obj
def list_members(obj, chat_id: str, query: str, admin, limit):
    signer = get_signer(None, obj)
    chat_id = chat_id.strip()
    if chat_id.startswith("@"):
        chat_id = chat_id[1:]
    else:
        try:
            chat_id = int(chat_id)
        except ValueError:
            raise click.UsageError("chat_id为username时必须以@开头")
    signer.app_run(signer.list_members(chat_id, query, admin=admin, limit=limit))


@tg_signer.command(
    help="""导出配置，默认为输出到终端。\n\n e.g.\n\n  tg-signer export -O config.json mytask\n\n  tg-signer export mytask > config.json"""
)
@click.argument("task_name")
@click.option(
    "--file", "-O", "file", type=click.Path(), default=None, help="导出至该文件"
)
@click.pass_obj
def export(obj, task_name: str, file: str = None):
    signer = get_signer(task_name, obj)
    data = signer.export()
    if not file:
        click.echo(data)
    else:
        with click.open_file(file, "w", encoding="utf-8") as fp:
            fp.write(data)


@tg_signer.command(
    name="import",
    help="""导入配置，默认为从终端读取。\n\n e.g.\n\n  tg-signer import -I config.json mytask\n\n  cat config.json | tg-signer import mytask""",
)
@click.argument("task_name")
@click.option(
    "--file", "-I", "file", type=click.Path(), default=None, help="导入该文件"
)
@click.pass_obj
def import_(obj, task_name: str, file: str = None):
    signer = get_signer(task_name, obj)
    if not file:
        stdin_text = click.get_text_stream("stdin")
        data = stdin_text.read()
    else:
        with click.open_file(file, "r", encoding="utf-8") as fp:
            data = fp.read()
    signer.import_(data)


@tg_signer.command(help="批量配置Telegram自带的定时发送消息功能")
@click.argument(
    "chat_id",
    type=int,
)
@click.argument("text")
@click.option(
    "--crontab",
    "-C",
    "crontab",
    type=str,
    required=True,
    help=" `crontab`语法, 如'0 0 * * *'表示每天0点发送.",
)
@click.option(
    "--next-times",
    "-N",
    "next_times",
    type=int,
    default=1,
    show_default=True,
    help="配置定时发送消息时的次数，如通过crontab配置了'每天0点发送消息'，则'30'表示将定时任务排30次，即未来30天每天0点发送消息",
)
@click.option(
    "--random-seconds",
    "-RS",
    "random_seconds",
    type=int,
    default=0,
    show_default=True,
    help="加入随机秒数，会应用于每个定时消息",
)
@click.pass_obj
def schedule_messages(obj, chat_id, text, crontab, next_times, random_seconds):
    signer = get_signer(None, obj)
    signer.app_run(
        signer.schedule_messages(chat_id, text, crontab, next_times, random_seconds)
    )


@tg_signer.command(help="显示已配置的定时消息")
@click.argument("chat_id", type=int)
@click.pass_obj
def list_schedule_messages(obj, chat_id):
    logging.root.setLevel(
        level=logging.WARNING,
    )
    signer = get_signer(None, obj)
    signer.app_run(signer.get_schedule_messages(chat_id))


@tg_signer.command(name="multi-run", help="使用一套配置同时运行多个账号")
@click.argument("task_name", nargs=1, default="my_sign")
@click.option(
    "--account",
    "-a",
    "accounts",
    required=True,
    multiple=True,
    help="多个account，每个account是一个自定义账号名称，对应session文件名为<account>.session",
)
@click.option(
    "--num-of-dialogs",
    "-n",
    default=50,
    show_default=True,
    type=int,
    help="获取最近N个对话, 请确保想要签到的对话在最近N个对话内",
)
@click.pass_obj
def multi_run(obj, accounts, task_name, num_of_dialogs):
    logger = logging.getLogger("tg-signer")
    logger.info(f"开始使用一套配置({task_name})同时运行多个账号..")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    coros = []
    for account in accounts:
        obj["account"] = account
        signer = get_signer(task_name, obj, loop=loop)
        coros.append(signer.run(num_of_dialogs))
    loop.run_until_complete(asyncio.gather(*coros))


@tg_signer.command(name="llm-config", help="配置大模型API")
@click.pass_obj
def llm_config(obj):
    from tg_signer.ai_tools import OpenAIConfigManager

    cfg_manager = OpenAIConfigManager(obj["workdir"])
    cfg_manager.ask_for_config()
