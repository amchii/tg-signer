import click
from click import Context, HelpFormatter

from tg_signer.signer import UserSigner, get_proxy


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
@click.pass_context
def tg_signer(
    ctx: click.Context,
    log_level: str,
    log_file: str,
    proxy: str,
    session_dir: str,
    account: str,
    workdir: str,
):
    from tg_signer.logger import configure_logger

    logger = configure_logger(log_level, log_file)
    ctx.ensure_object(dict)
    proxy = get_proxy(proxy)
    if proxy and ctx.invoked_subcommand in [
        "login",
        "run",
        "run-once",
        "send-text",
        "logout",
    ]:
        logger.info(
            "Using proxy: %s"
            % f"{proxy['scheme']}://{proxy['hostname']}:{proxy['port']}"
        )
    ctx.obj["proxy"] = proxy
    ctx.obj["session_dir"] = session_dir
    ctx.obj["account"] = account
    ctx.obj["workdir"] = workdir


@tg_signer.command(help="Show version")
def version():
    from tg_signer import __version__

    s = f"tg-signer {__version__}"
    click.echo(s)


@tg_signer.command(name="list", help="列出已有配置")
def list_():
    return UserSigner().list_()


@tg_signer.command(help="登录账号（用于获取session）")
@click.option(
    "--num-of-dialogs",
    "-n",
    default=20,
    show_default=True,
    type=int,
    help="获取最近N个对话, 请确保想要签到的对话在最近N个对话内",
)
@click.pass_obj
def login(obj, num_of_dialogs):
    signer = UserSigner(
        account=obj["account"],
        proxy=obj["proxy"],
        session_dir=obj["session_dir"],
        workdir=obj["workdir"],
    )
    signer.app_run(signer.login(num_of_dialogs))


@tg_signer.command(help="登出账号并删除session文件")
@click.pass_obj
def logout(obj):
    signer = UserSigner(
        account=obj["account"],
        proxy=obj["proxy"],
        session_dir=obj["session_dir"],
        workdir=obj["workdir"],
    )
    signer.app_run(signer.logout())


@tg_signer.command(help="根据任务配置运行签到")
@click.argument("task_name", nargs=1, default="my_sign")
@click.option(
    "--num-of-dialogs",
    "-n",
    default=20,
    show_default=True,
    type=int,
    help="获取最近N个对话, 请确保想要签到的对话在最近N个对话内",
)
@click.pass_obj
def run(obj, task_name, num_of_dialogs):
    signer = UserSigner(
        account=obj["account"],
        task_name=task_name,
        proxy=obj["proxy"],
        session_dir=obj["session_dir"],
        workdir=obj["workdir"],
    )
    signer.app_run(signer.run(num_of_dialogs))


@tg_signer.command(help="运行一次签到任务，即使该签到任务今日已执行过")
@click.argument("task_name", default="my_sign")
@click.option(
    "--num-of-dialogs",
    "-n",
    default=20,
    show_default=True,
    type=int,
    help="获取最近N个对话, 请确保想要签到的对话在最近N个对话内",
)
@click.pass_obj
def run_once(obj, task_name, num_of_dialogs):
    signer = UserSigner(
        account=obj["account"],
        task_name=task_name,
        proxy=obj["proxy"],
        session_dir=obj["session_dir"],
        workdir=obj["workdir"],
    )
    signer.app_run(signer.run_once(num_of_dialogs))


@tg_signer.command(help='发送一次消息, 请确保当前会话已经"见过"该`chat_id`')
@click.argument(
    "chat_id",
    type=int,
)
@click.argument(
    "text",
)
@click.pass_obj
def send_text(obj, chat_id, text):
    singer = UserSigner(
        account=obj["account"],
        proxy=obj["proxy"],
        session_dir=obj["session_dir"],
        workdir=obj["workdir"],
    )
    singer.app_run(singer.send_text(chat_id, text))


@tg_signer.command(help="重新配置")
@click.argument("task_name", nargs=1, default="my_sign")
def reconfig(task_name):
    signer = UserSigner(task_name=task_name)
    return signer.reconfig()
