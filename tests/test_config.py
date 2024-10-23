import pytest

from tg_signer.config import MatchConfig


class TestMatchConfig:

    def test_match_exact(self):
        config = MatchConfig(chat_id=123, rule="exact", rule_value="hello")
        assert config.match(chat_id=123, text="hello") is True
        assert config.match(chat_id=123, text="hELlo") is True
        assert config.match(chat_id=123, text="hello world") is False

        config.ignore_case = False
        assert config.match(chat_id=123, text="hELlo") is False

    def test_match_contains(self):
        config = MatchConfig(chat_id=123, rule="contains", rule_value="world")
        assert config.match(chat_id=123, text="hello world") is True
        assert config.match(chat_id=123, text="hello World") is True
        assert config.match(chat_id=123, text="hello") is False

        config.ignore_case = False
        assert config.match(chat_id=123, text="hello World") is False

    def test_match_regex(self):
        config = MatchConfig(chat_id=123, rule="regex", rule_value="^hello")
        assert config.match(chat_id=123, text="hello world") is True
        assert config.match(chat_id=123, text="HelLo world") is True
        assert config.match(chat_id=123, text="world hello") is False

        config.ignore_case = False
        assert config.match(chat_id=123, text="HelLo world") is False

    def test_match_from_user_id(self):
        config = MatchConfig(
            chat_id=123, rule="exact", rule_value="hello", from_user_ids=[456]
        )
        assert config.match(chat_id=123, text="hello", from_user_id=456) is True
        assert config.match(chat_id=123, text="hello", from_user_id=654) is False

    def test_match_chat_id(self):
        config = MatchConfig(chat_id=123, rule="exact", rule_value="hello")
        assert config.match(chat_id=321, text="hello") is False

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
