from datetime import time

from tg_signer.config import (
    ChooseOptionByImageAction,
    ClickKeyboardByTextAction,
    ReplyByCalculationProblemAction,
    SendDiceAction,
    SendTextAction,
    SignChatV2,
    SignConfigV1,
    SignConfigV2,
    SignConfigV3,
)


class TestSignConfigV2ToCurrent:
    """测试 SignConfigV2.to_current 方法"""

    def test_convert_basic_chat(self):
        """测试基础聊天配置转换"""
        v2_config = SignConfigV2(
            chats=[
                SignChatV2(
                    chat_id=123,
                    sign_text="Hello",
                    delete_after=10,
                )
            ],
            sign_at="08:00",
            random_seconds=300,
        )

        v3_config = SignConfigV2.to_current(v2_config)

        assert isinstance(v3_config, SignConfigV3)
        assert v3_config.sign_at == "08:00"
        assert v3_config.random_seconds == 300
        assert len(v3_config.chats) == 1

        chat = v3_config.chats[0]
        assert chat.chat_id == 123
        assert chat.delete_after == 10
        assert len(chat.actions) == 1
        assert isinstance(chat.actions[0], SendTextAction)
        assert chat.actions[0].text == "Hello"

    def test_convert_dice_chat(self):
        """测试 Dice 表情配置转换"""
        v2_config = SignConfigV2(
            chats=[
                SignChatV2(
                    chat_id=123,
                    sign_text="🎲",
                    as_dice=True,
                )
            ],
            sign_at="08:00",
        )

        v3_config = SignConfigV2.to_current(v2_config)
        action = v3_config.chats[0].actions[0]

        assert isinstance(action, SendDiceAction)
        assert action.dice == "🎲"

    def test_convert_complex_chat(self):
        """测试包含多种操作的复杂配置转换"""
        v2_config = SignConfigV2(
            chats=[
                SignChatV2(
                    chat_id=123,
                    sign_text="签到",
                    text_of_btn_to_click="点击",
                    choose_option_by_image=True,
                    has_calculation_problem=True,
                )
            ],
            sign_at="08:00",
        )

        v3_config = SignConfigV2.to_current(v2_config)
        actions = v3_config.chats[0].actions

        assert len(actions) == 4
        assert isinstance(actions[0], SendTextAction)
        assert actions[0].text == "签到"
        assert isinstance(actions[1], ClickKeyboardByTextAction)
        assert actions[1].text == "点击"
        assert isinstance(actions[2], ChooseOptionByImageAction)
        assert isinstance(actions[3], ReplyByCalculationProblemAction)

    def test_convert_multiple_chats(self):
        """测试多个聊天配置转换"""
        v2_config = SignConfigV2(
            chats=[
                SignChatV2(chat_id=1, sign_text="Chat1"),
                SignChatV2(chat_id=2, sign_text="Chat2"),
            ],
            sign_at="08:00",
        )

        v3_config = SignConfigV2.to_current(v2_config)

        assert len(v3_config.chats) == 2
        assert v3_config.chats[0].chat_id == 1
        assert v3_config.chats[0].actions[0].text == "Chat1"
        assert v3_config.chats[1].chat_id == 2
        assert v3_config.chats[1].actions[0].text == "Chat2"

    def test_convert_empty_actions(self):
        """测试空操作列表的情况"""
        v2_config = SignConfigV2(
            chats=[SignChatV2(chat_id=123, sign_text="")],
            sign_at="08:00",
        )

        v3_config = SignConfigV2.to_current(v2_config)

        assert len(v3_config.chats[0].actions) == 0

    def test_convert_from_v1(self):
        """测试从 V1 配置升级到 V3"""
        v1_config = SignConfigV1(
            chat_id=123,
            sign_text="Old config",
            sign_at=time(8, 0),
            random_seconds=300,
        )

        # 通过 V2 的 load 方法触发转换
        v3_config = SignConfigV2.to_current(v1_config)

        assert isinstance(v3_config, SignConfigV3)
        assert v3_config.sign_at == "08:00:00"  # time 对象被转换为字符串
        assert v3_config.random_seconds == 300
        assert len(v3_config.chats) == 1
        assert v3_config.chats[0].chat_id == 123
        assert v3_config.chats[0].actions[0].text == "Old config"
