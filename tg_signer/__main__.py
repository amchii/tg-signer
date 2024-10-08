__all__ = ("cli",)

import sys


def cli():
    from .cli import tg_signer

    sys.exit(tg_signer())
