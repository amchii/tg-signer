__all__ = ("signer",)

import sys


def signer():
    from tg_signer import cli

    sys.exit(cli.tg_signer())
