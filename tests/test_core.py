import pytest
from tg_signer.core import BaseUserWorker, UserMonitor, UserSigner  # noqa: F401


class TestBaseUserWorker:
    @pytest.mark.asyncio
    async def test(self):
        BaseUserWorker()
