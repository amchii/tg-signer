import logging

import click
from click import Group

from tg_signer.core import UserMonitor

from .signer import tg_signer


def get_monitor(task_name, ctx_obj: dict):
    monitor = UserMonitor(
        task_name=task_name,
        account=ctx_obj["account"],
        proxy=ctx_obj["proxy"],
        session_dir=ctx_obj["session_dir"],
        workdir=ctx_obj["workdir"],
        session_string=ctx_obj["session_string"],
        in_memory=ctx_obj["in_memory"],
    )
    return monitor


@tg_signer.group(name="monitor", help="配置和运行监控")
@click.pass_context
def tg_monitor(ctx: click.Context):
    logger = logging.getLogger("tg-signer")
    if ctx.invoked_subcommand in [
        "run",
    ]:
        if proxy := ctx.obj.get("proxy"):
            logger.info(
                "Using proxy: %s"
                % f"{proxy['scheme']}://{proxy['hostname']}:{proxy['port']}"
            )
        logger.info(f"Using account: {ctx.obj['account']}")


tg_monitor: Group


@tg_monitor.command(name="list", help="列出已有配置")
@click.pass_obj
def list_(obj):
    return UserMonitor(workdir=obj["workdir"]).list_()


@tg_monitor.command(help="根据配置运行监控")
@click.argument("task_name", nargs=1, default="my_monitor")
@click.option(
    "--num-of-dialogs",
    "-n",
    default=20,
    show_default=True,
    type=int,
    help="获取最近N个对话, 请确保想要监控的对话在最近N个对话内",
)
@click.pass_obj
def run(obj, task_name, num_of_dialogs):
    monitor = get_monitor(task_name, obj)
    monitor.app_run(monitor.run(num_of_dialogs))


@tg_monitor.command(help="重新配置")
@click.argument("task_name", nargs=1, default="my_monitor")
@click.pass_obj
def reconfig(obj, task_name):
    signer = UserMonitor(task_name=task_name, workdir=obj["workdir"])
    return signer.reconfig()


@tg_monitor.command(
    help="""导出配置，默认为输出到终端。\n\n e.g.\n\n  tg-monitor export -O config.json mytask\n\n  tg-monitor export mytask > config.json"""
)
@click.argument("task_name")
@click.option(
    "--file", "-O", "file", type=click.Path(), default=None, help="导出至该文件"
)
@click.pass_obj
def export(obj, task_name: str, file: str = None):
    monitor = get_monitor(task_name, obj)
    data = monitor.export()
    if not file:
        click.echo(data)
    else:
        with click.open_file(file, "w", encoding="utf-8") as fp:
            fp.write(data)


@tg_monitor.command(
    name="import",
    help="""导入配置，默认为从终端读取。\n\n e.g.\n\n  tg-monitor import -I config.json mytask\n\n  cat config.json | tg-monitor import mytask""",
)
@click.argument("task_name")
@click.option(
    "--file", "-I", "file", type=click.Path(), default=None, help="导入该文件"
)
@click.pass_obj
def import_(obj, task_name: str, file: str = None):
    monitor = get_monitor(task_name, obj)
    if not file:
        stdin_text = click.get_text_stream("stdin")
        data = stdin_text.read()
    else:
        with click.open_file(file, "r", encoding="utf-8") as fp:
            data = fp.read()
    monitor.import_(data)
