from typing import Callable, List, Optional

from nicegui import ui
from nicegui.events import ValueChangeEventArguments
from pydantic import ValidationError

from tg_signer.config import (
    ActionT,
    ChooseOptionByImageAction,
    ClickKeyboardByTextAction,
    ReplyByCalculationProblemAction,
    SendDiceAction,
    SendTextAction,
    SignChatV3,
    SignConfigV3,
    SupportAction,
)
from tg_signer.webui.data import load_user_infos, save_config


class InteractiveSignerConfig:
    def __init__(
        self,
        workdir,
        on_complete: Callable[[], None],
        initial_config: Optional[dict] = None,
        initial_name: str = "",
    ):
        self.workdir = workdir
        self.on_complete = on_complete
        self.dialog = ui.dialog()
        with self.dialog, ui.card().classes("w-full max-w-4xl h-[90vh] flex flex-col"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("交互式配置向导").classes("text-xl font-bold")
                ui.button(icon="close", on_click=self.dialog.close).props(
                    "flat round dense"
                )

            self.content_area = ui.scroll_area().classes("w-full flex-grow p-4")

            # State
            self.task_name = initial_name or "my_sign"
            self.sign_at = "06:00:00"
            self.random_seconds = 0
            self.chats: List[SignChatV3] = []

            if initial_config:
                try:
                    loaded = SignConfigV3.load(initial_config)
                    if loaded:
                        cfg, _ = loaded
                        self.sign_at = cfg.sign_at
                        self.random_seconds = cfg.random_seconds
                        self.chats = list(cfg.chats)
                except Exception as e:
                    ui.notify(f"加载现有配置失败: {e}", type="warning")

            self.render_main_form()

    def open(self):
        self.dialog.open()

    def render_main_form(self):
        self.content_area.clear()
        with self.content_area:
            # Basic Settings
            ui.label("1. 基础设置").classes("text-lg font-semibold mb-2")
            with ui.grid(columns=2).classes("w-full gap-4 mb-6"):
                ui.input(
                    label="任务名称",
                    value=self.task_name,
                    on_change=lambda e: setattr(self, "task_name", e.value),
                ).props("outlined")

                ui.input(
                    label="签到时间 (Time or Cron)",
                    value=self.sign_at,
                    placeholder="06:00:00 or 0 6 * * *",
                    on_change=lambda e: setattr(self, "sign_at", e.value),
                ).props("outlined")

                ui.number(
                    label="随机延迟 (秒)",
                    value=self.random_seconds,
                    min=0,
                    on_change=lambda e: setattr(
                        self, "random_seconds", int(e.value or 0)
                    ),
                ).props("outlined")

            # Chats Management
            with ui.row().classes("w-full items-center justify-between mb-2"):
                ui.label("2. 签到任务列表").classes("text-lg font-semibold")
                ui.button("添加任务", icon="add", on_click=self.open_chat_dialog)

            self.chats_container = ui.column().classes("w-full gap-2")
            self.refresh_chats_list()

            # Footer Actions
            with ui.row().classes("w-full justify-end mt-6 gap-2"):
                ui.button("取消", on_click=self.dialog.close).props("flat")
                ui.button("保存配置", icon="save", on_click=self.save_all)

    def refresh_chats_list(self):
        self.chats_container.clear()
        with self.chats_container:
            if not self.chats:
                ui.label("暂无任务，请点击右上角添加").classes(
                    "text-gray-500 italic w-full text-center py-4"
                )
                return

            for idx, chat in enumerate(self.chats):
                with ui.card().classes("w-full p-2"):
                    with ui.row().classes("w-full items-center gap-4"):
                        ui.label(f"#{idx + 1}").classes("font-bold text-gray-500")
                        with ui.column().classes("flex-grow gap-0"):
                            ui.label(f"Chat ID: {chat.chat_id}").classes("font-medium")
                            if chat.name:
                                ui.label(f"Name: {chat.name}").classes(
                                    "text-sm text-gray-500"
                                )
                            ui.label(f"Actions: {len(chat.actions)}").classes(
                                "text-xs bg-blue-100 px-2 rounded-full w-fit"
                            )

                        with ui.row().classes("gap-1"):
                            ui.button(
                                icon="edit", on_click=lambda _, i=idx: self.edit_chat(i)
                            ).props("flat round dense")
                            ui.button(
                                icon="delete",
                                color="negative",
                                on_click=lambda _, i=idx: self.delete_chat(i),
                            ).props("flat round dense")

    def delete_chat(self, index: int):
        self.chats.pop(index)
        self.refresh_chats_list()

    def edit_chat(self, index: int):
        self.open_chat_dialog(chat=self.chats[index], index=index)

    def open_chat_dialog(self, chat: Optional[SignChatV3] = None, index: int = -1):
        # Chat Dialog State
        d_chat_id = chat.chat_id if chat else None
        d_name = chat.name if chat else ""
        d_delete_after = chat.delete_after if chat else None
        d_actions: List[ActionT] = list(chat.actions) if chat else []

        dialog = ui.dialog()
        with dialog, ui.card().classes("w-full max-w-2xl"):
            ui.label("编辑任务" if chat else "添加任务").classes(
                "text-lg font-bold mb-4"
            )

            # Quick Import Dialog
            def show_import_dialog():
                user_infos = load_user_infos(self.workdir)
                if not user_infos:
                    ui.notify("未找到用户信息", type="warning")
                    return

                with ui.dialog() as import_dialog, ui.card().classes("w-full max-w-lg"):
                    ui.label("从最近聊天快速导入").classes("text-lg font-bold mb-4")

                    def on_chat_select(e: ValueChangeEventArguments):
                        selected_chat = e.value
                        if not selected_chat:
                            return

                        chat_id, label = selected_chat
                        # Auto fill ID
                        id_input.value = chat_id

                        # Auto fill name if empty
                        if not name_input.value:
                            name_input.value = label

                        import_dialog.close()

                    def on_user_select(e):
                        user_id = e.value
                        chat_select.options = {}
                        chat_select.value = None

                        if not user_id:
                            chat_select.disable()
                            return

                        target_user = next(
                            (u for u in user_infos if u.user_id == user_id), None
                        )
                        if target_user and target_user.latest_chats:
                            options = {}
                            for c in target_user.latest_chats:
                                label = c.get("title") or c.get("first_name") or "N/A"
                                username = c.get("username")
                                if username:
                                    label += f" (@{username})"
                                value = (c["id"], label)
                                options[value] = label
                            chat_select.options = options
                            chat_select.enable()
                        else:
                            chat_select.disable()
                            ui.notify("该用户无最近聊天记录", type="warning")

                    with ui.column().classes("w-full gap-4"):
                        user_options = {
                            u.user_id: f"{u.user_id} ({u.data.get('first_name', '')})"
                            for u in user_infos
                        }
                        ui.select(
                            options=user_options,
                            label="选择用户",
                            on_change=on_user_select,
                            with_input=True,
                        ).classes("w-full")

                        chat_select = ui.select(
                            options={},
                            label="选择聊天",
                            on_change=on_chat_select,
                            with_input=True,
                        ).classes("w-full")
                        chat_select.disable()

                    ui.button("取消", on_click=import_dialog.close).props(
                        "flat"
                    ).classes("ml-auto mt-4")

                import_dialog.open()

            with ui.grid(columns=2).classes("w-full gap-4 mb-4"):
                id_input = (
                    ui.input(
                        label="Chat ID",
                        value=str(d_chat_id) if d_chat_id else "",
                        placeholder="整数ID (点击选择)",
                    )
                    .props("outlined")
                    .on("click", show_import_dialog)
                )

                name_input = ui.input(label="备注名称 (可选)", value=d_name).props(
                    "outlined"
                )

                del_input = ui.number(
                    label="发送后删除 (秒)",
                    value=d_delete_after,
                    placeholder="留空不删除",
                ).props("outlined")

            # Actions Section
            with ui.row().classes("w-full items-center justify-between mb-2"):
                ui.label("动作列表 (按顺序执行)").classes("font-semibold")

            actions_container = ui.column().classes(
                "w-full gap-2 mb-4 p-2 bg-gray-50 rounded"
            )

            def refresh_actions():
                actions_container.clear()
                with actions_container:
                    if not d_actions:
                        ui.label("暂无动作").classes("text-gray-500 italic text-sm")
                    for i, action in enumerate(d_actions):
                        with ui.row().classes(
                            "w-full items-center justify-between bg-white p-2 rounded shadow-sm"
                        ):
                            desc = f"{i + 1}. [{action.action.desc}]"
                            detail = ""
                            if isinstance(action, SendTextAction):
                                detail = action.text
                            elif isinstance(action, SendDiceAction):
                                detail = action.dice
                            elif isinstance(action, ClickKeyboardByTextAction):
                                detail = action.text

                            ui.label(f"{desc} {detail}").classes("text-sm")
                            ui.button(
                                icon="delete",
                                color="negative",
                                on_click=lambda _, idx=i: remove_action(idx),
                            ).props("flat round dense size=sm")

            def remove_action(idx):
                d_actions.pop(idx)
                refresh_actions()

            def add_action_ui():
                with ui.dialog() as act_dialog, ui.card():
                    ui.label("添加动作").classes("font-bold")
                    act_type = ui.select(
                        options={a: a.desc for a in SupportAction},
                        label="动作类型",
                        value=SupportAction.SEND_TEXT,
                    ).classes("w-full")

                    # Dynamic fields container
                    fields_container = ui.column().classes("w-full")

                    # Store input references
                    inputs = {}

                    def update_fields():
                        fields_container.clear()
                        inputs.clear()
                        t = act_type.value
                        with fields_container:
                            if t == SupportAction.SEND_TEXT:
                                inputs["text"] = ui.input("发送文本").classes("w-full")
                            elif t == SupportAction.SEND_DICE:
                                inputs["dice"] = ui.select(
                                    options=["🎲", "🎯", "🏀", "⚽", "🎳", "🎰"],
                                    label="选择骰子",
                                    value="🎲",
                                ).classes("w-full")
                            elif t == SupportAction.CLICK_KEYBOARD_BY_TEXT:
                                inputs["text"] = ui.input("按钮文本").classes("w-full")
                            elif t == SupportAction.CHOOSE_OPTION_BY_IMAGE:
                                ui.label("将使用AI识别图片并选择").classes(
                                    "text-sm text-gray-500"
                                )
                            elif t == SupportAction.REPLY_BY_CALCULATION_PROBLEM:
                                ui.label("将使用AI回答计算题").classes(
                                    "text-sm text-gray-500"
                                )

                    act_type.on_value_change(update_fields)
                    update_fields()  # Init

                    def confirm_add_action():
                        t = act_type.value
                        try:
                            new_action = None
                            if t == SupportAction.SEND_TEXT:
                                txt = inputs["text"].value
                                if not txt:
                                    raise ValueError("请输入文本")
                                new_action = SendTextAction(text=txt)
                            elif t == SupportAction.SEND_DICE:
                                new_action = SendDiceAction(dice=inputs["dice"].value)
                            elif t == SupportAction.CLICK_KEYBOARD_BY_TEXT:
                                txt = inputs["text"].value
                                if not txt:
                                    raise ValueError("请输入按钮文本")
                                new_action = ClickKeyboardByTextAction(text=txt)
                            elif t == SupportAction.CHOOSE_OPTION_BY_IMAGE:
                                new_action = ChooseOptionByImageAction()
                            elif t == SupportAction.REPLY_BY_CALCULATION_PROBLEM:
                                new_action = ReplyByCalculationProblemAction()

                            if new_action:
                                d_actions.append(new_action)
                                refresh_actions()
                                act_dialog.close()
                        except Exception as e:
                            ui.notify(str(e), type="negative")

                    ui.button("确定添加", on_click=confirm_add_action).classes(
                        "w-full mt-2"
                    )
                act_dialog.open()

            refresh_actions()
            ui.button("添加动作", icon="add", on_click=add_action_ui).classes(
                "w-full mb-4"
            ).props("outline dashed")

            def save_chat():
                try:
                    try:
                        cid = int(id_input.value)
                    except (ValueError, TypeError):
                        raise ValueError("Chat ID不能为空且必须是整数")

                    if not d_actions:
                        raise ValueError("至少需要配置一个动作")

                    first_action = d_actions[0]
                    if first_action.action not in [
                        SupportAction.SEND_TEXT,
                        SupportAction.SEND_DICE,
                    ]:
                        raise ValueError(
                            f"第一个动作必须为「{SupportAction.SEND_TEXT.desc}」或「{SupportAction.SEND_DICE.desc}」"
                        )

                    new_chat = SignChatV3(
                        chat_id=cid,
                        name=name_input.value.strip() or None,
                        delete_after=int(del_input.value) if del_input.value else None,
                        actions=d_actions,
                    )

                    if index >= 0:
                        self.chats[index] = new_chat
                    else:
                        self.chats.append(new_chat)

                    self.refresh_chats_list()
                    dialog.close()
                except ValueError as e:
                    ui.notify(str(e), type="negative")
                except ValidationError as e:
                    ui.notify(f"验证失败: {e}", type="negative")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("取消", on_click=dialog.close).props("flat")
                ui.button("确定", on_click=save_chat)

        dialog.open()

    def save_all(self):
        try:
            if not self.task_name:
                raise ValueError("任务名称不能为空")
            if not self.chats:
                raise ValueError("请至少添加一个签到任务")

            # Validate config
            config = SignConfigV3(
                chats=self.chats,
                sign_at=self.sign_at,
                random_seconds=self.random_seconds,
            )

            save_config("signer", self.task_name, config, workdir=self.workdir)
            ui.notify(f"配置 {self.task_name} 保存成功", type="positive")
            self.dialog.close()
            self.on_complete()

        except ValidationError as e:
            ui.notify(f"配置验证失败: {e}", type="negative")
        except ValueError as e:
            ui.notify(str(e), type="negative")
        except Exception as e:
            ui.notify(f"保存失败: {e}", type="negative")
