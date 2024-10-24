import logging

import click

from tg_signer.core import UserMonitor

from .signer import tg_signer


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
    monitor = UserMonitor(
        task_name=task_name,
        session_dir=obj["session_dir"],
        account=obj["account"],
        proxy=obj["proxy"],
        workdir=obj["workdir"],
    )
    monitor.app_run(monitor.run(num_of_dialogs))


@tg_monitor.command(help="重新配置")
@click.argument("task_name", nargs=1, default="my_monitor")
@click.pass_obj
def reconfig(obj, task_name):
    signer = UserMonitor(task_name=task_name, workdir=obj["workdir"])
    return signer.reconfig()
