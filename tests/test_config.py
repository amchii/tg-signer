from unittest.mock import MagicMock

import pytest

from tg_signer.config import MatchConfig


class TestMatchConfig:

    @pytest.mark.parametrize(
        "chat_id, rule, rule_value, from_user_ids, message_from_user, expected",
        [
            (123, "exact", "test", [456], {"id": 456}, True),
            (123, "exact", "test", ["@username"], {"username": "username"}, True),
            (123, "exact", "test", None, {"id": 789}, True),
            (123, "exact", "test", [456], {"id": 789}, False),
            (123, "exact", "test", ["@Username"], {"username": "username"}, True),
            (123, "exact", "test", ["@username"], {"username": "wrongusername"}, False),
            (123, "exact", "test", ["me"], {"is_self": True}, True),
        ],
    )
    def test_match_user(
        self, chat_id, rule, rule_value, from_user_ids, message_from_user, expected
    ):
        config = MatchConfig(
            chat_id=chat_id,
            rule=rule,
            rule_value=rule_value,
            from_user_ids=from_user_ids,
        )
        message = MagicMock()
        message.from_user = MagicMock(**message_from_user)
        assert config.match_user(message) == expected

    # 测试用例集
    @pytest.mark.parametrize(
        "rule, rule_value, text, ignore_case, expected",
        [
            # Exact matching
            ("exact", "hello", "hello", False, True),
            ("exact", "hello", "hello", True, True),
            ("exact", "hello", "world", False, False),
            # Contains matching
            ("contains", "hello", "hello world", False, True),
            ("contains", "hello", "world hello", False, True),
            ("contains", "hello", "world", False, False),
            # Regex matching
            ("regex", r"\bhello\b", "hello world", False, True),
            ("regex", r"\bhello\b", "world hello", False, True),
            ("regex", r"\bhello\b", "world", False, False),
            # Case insensitivity
            ("exact", "hello", "HELLO", True, True),
            ("contains", "hello", "HELLO WORLD", True, True),
            ("regex", r"\bhello\b", "HELLO WORLD", True, True),
        ],
    )
    def test_match_text(self, rule, rule_value, text, ignore_case, expected):
        # 构建 MatchConfig 实例
        config = MatchConfig(rule=rule, rule_value=rule_value, ignore_case=ignore_case)
        # 进行匹配测试
        assert config.match_text(text) == expected

    # 测试默认文本情况
    def test_get_send_text_default(self):
        config = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="hello",
            default_send_text="default text",
            send_text_search_regex=None,
        )
        assert config.get_send_text("any text") == "default text"

    # 测试正则表达式匹配情况
    @pytest.mark.parametrize(
        "regex, text, expected",
        [
            (r"hello (\w+)", "hello world", "world"),
            (r"hello (\w+)", "hello", "default text"),
            (r"hello (\w+)", "hello 123", "123"),
        ],
    )
    def test_get_send_text_with_regex(self, regex, text, expected):
        config = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="hello",
            default_send_text="default text",
            send_text_search_regex=regex,
        )
        assert config.get_send_text(text) == expected

    # 测试正则表达式不匹配情况
    def test_get_send_text_no_match(self):
        config = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="hello",
            default_send_text="default text",
            send_text_search_regex=r"hello (\w+)",
        )
        assert config.get_send_text("goodbye world") == "default text"

    # 测试正则表达式匹配但没有捕获组情况
    def test_get_send_text_no_capture_group(self):
        config = MatchConfig(
            chat_id=123,
            rule="exact",
            rule_value="hello",
            default_send_text="default text",
            send_text_search_regex=r"hello",
        )
        with pytest.raises(ValueError) as excinfo:
            config.get_send_text("hello world")
        assert (
            str(excinfo.value)
            == f"{config}: 消息文本: 「hello world」匹配成功但未能捕获关键词, 请检查正则表达式"
        )
