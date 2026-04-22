import pathlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest


def require_zoneinfo(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        pytest.skip(f"zoneinfo data for {name} is unavailable in this environment")


def get_test_tzfile_source() -> pathlib.Path:
    for path_str in ("/etc/localtime", "/usr/share/zoneinfo/UTC"):
        path = pathlib.Path(path_str)
        if path.is_file():
            return path
    pytest.skip("no system tzfile is available for this test")


def test_get_timezone_prefers_tz_environment(monkeypatch):
    import tg_signer.utils as utils

    expected = require_zoneinfo("America/New_York")
    monkeypatch.setenv("TZ", "America/New_York")
    monkeypatch.setattr(utils, "_get_local_timezone", lambda: timezone.utc)

    tz = utils.get_timezone()

    assert getattr(tz, "key", None) == expected.key


def test_get_timezone_supports_posix_prefixed_tz_name(monkeypatch):
    import tg_signer.utils as utils

    expected = require_zoneinfo("America/New_York")
    monkeypatch.setenv("TZ", ":America/New_York")
    monkeypatch.setattr(utils, "_get_local_timezone", lambda: timezone.utc)

    tz = utils.get_timezone()

    assert getattr(tz, "key", None) == expected.key


def test_get_timezone_supports_tzfile_path_in_tz_environment(monkeypatch, tmp_path):
    import tg_signer.utils as utils

    tzfile = tmp_path / "localtime"
    tzfile.write_bytes(get_test_tzfile_source().read_bytes())
    expected = utils._load_timezone_from_file(tzfile)
    assert expected is not None

    monkeypatch.setenv("TZ", f":{tzfile}")
    monkeypatch.setattr(utils, "_get_local_timezone", lambda: timezone.utc)

    tz = utils.get_timezone()
    sample = datetime(2026, 4, 14, 12, 0)

    assert (
        sample.replace(tzinfo=tz).utcoffset()
        == sample.replace(tzinfo=expected).utcoffset()
    )


def test_get_timezone_uses_local_timezone_when_tz_missing(monkeypatch):
    import tg_signer.utils as utils

    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setattr(utils, "_get_local_timezone", lambda: timezone.utc)

    tz = utils.get_timezone()

    assert tz is timezone.utc


def test_get_timezone_falls_back_to_local_timezone_when_tz_is_invalid(monkeypatch):
    import tg_signer.utils as utils

    monkeypatch.setenv("TZ", "Invalid/Zone")
    monkeypatch.setattr(utils, "_get_local_timezone", lambda: timezone.utc)

    tz = utils.get_timezone()

    assert tz is timezone.utc


def test_get_timezone_falls_back_to_asia_shanghai(monkeypatch):
    import tg_signer.utils as utils

    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setattr(utils, "_get_local_timezone", lambda: None)

    tz = utils.get_timezone()
    sample = datetime(2026, 1, 1, 12, 0)

    assert sample.replace(tzinfo=tz).utcoffset() == timedelta(hours=8)


def test_get_local_timezone_uses_python_local_timezone(monkeypatch):
    import tg_signer.utils as utils

    expected = timezone.utc

    class FakeDateTime:
        @staticmethod
        def now(tz=None):
            assert tz is None
            return SimpleNamespace(astimezone=lambda: SimpleNamespace(tzinfo=expected))

    monkeypatch.setattr(utils, "datetime", FakeDateTime)

    assert utils._get_local_timezone() is expected
