import json
import os
from pathlib import Path
from typing import Callable, Dict

from nicegui import app, ui
from pydantic import TypeAdapter

from tg_signer.webui.data import (
    CONFIG_META,
    DEFAULT_LOG_FILE,
    DEFAULT_WORKDIR,
    LOG_DIR,
    ConfigKind,
    delete_config,
    get_workdir,
    list_log_files,
    list_task_names,
    load_config,
    load_logs,
    load_sign_records,
    load_user_infos,
    save_config,
)
from tg_signer.webui.interactive import InteractiveSignerConfig
from tg_signer.webui.schema_utils import clean_schema

SIGNER_TEMPLATE: Dict[str, object] = {
    "chats": [
        {
            "chat_id": 123456789,
            "name": "示例任务",
            "delete_after": None,
            "actions": [{"action": 1, "text": "签到"}],
            "action_interval": 1,
        }
    ],
    "sign_at": "0 6 * * *",
    "random_seconds": 0,
    "sign_interval": 1,
}

MONITOR_TEMPLATE: Dict[str, object] = {
    "match_cfgs": [
        {
            "chat_id": "@channel_or_user",
            "rule": "contains",
            "rule_value": "关键词",
            "from_user_ids": None,
            "always_ignore_me": False,
            "default_send_text": "自动回复",
            "ai_reply": False,
            "ai_prompt": None,
            "send_text_search_regex": None,
            "delete_after": None,
            "ignore_case": True,
            "forward_to_chat_id": None,
            "external_forwards": None,
            "push_via_server_chan": False,
            "server_chan_send_key": None,
        }
    ]
}


AUTH_CODE_ENV = "TG_SIGNER_GUI_AUTHCODE"
AUTH_STORAGE_KEY = "tg_signer_gui_auth_code"


class UIState:
    def __init__(self) -> None:
        self.workdir: Path = get_workdir(DEFAULT_WORKDIR)
        self.log_path: Path = DEFAULT_LOG_FILE
        self.log_limit: int = 200
        self.record_filter: str = ""

    def set_workdir(self, path_str: str) -> None:
        self.workdir = get_workdir(Path(path_str).expanduser())

    def set_log_path(self, path_str: str) -> None:
        self.log_path = Path(path_str).expanduser()


state = UIState()


def pretty_json(data: Dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def notify_error(exc: Exception) -> None:
    ui.notify(f"{exc}", type="negative")


class BaseConfigBlock:
    def __init__(
        self,
        kind: ConfigKind,
        template: Dict[str, object],
    ):
        self.kind = kind
        self.template = template
        self.title = "签到配置 (signer)" if kind == "signer" else "监控配置 (monitor)"
        self.root_dir, self.cfg_cls = CONFIG_META[kind]
        with ui.card().classes("w-full shadow-md"):
            ui.label(self.title).classes("text-lg font-semibold")
            ui.label(f"目录: {self.root_dir}/<name>/config.json").classes(
                "text-sm text-gray-500"
            )
            with ui.row().classes("items-end w-full gap-3"):
                self.select = ui.select(
                    label="选择配置",
                    options=[],
                    with_input=True,
                    on_change=self.load_current,
                ).classes("min-w-[240px]")
                ui.button("重置", on_click=self.clear_selection).props("outline")
                self.name_input = ui.input(
                    label="保存为/新建名称",
                    placeholder="my_task",
                ).classes("min-w-[200px]")
                ui.button("使用示例", on_click=self.fill_template)
                self.setup_toolbar()

            # MonitorConfig schema causes json_editor to fail rendering due to "format": "uri" etc.
            # We need to clean the schema before passing it to the editor.
            schema = TypeAdapter(self.cfg_cls | None).json_schema()
            if self.kind == "monitor":
                schema = clean_schema(schema)

            def on_change(e):
                self.editor.properties["content"] = e.content

            self.editor = ui.json_editor(
                {"content": {"json": None}},
                schema=schema,
                on_change=on_change,
            )
            self.selected_name: dict[str, str] = {"value": ""}

            with ui.row().classes("gap-2 items-center"):
                ui.button("刷新列表", on_click=self.refresh_options)
                ui.button("加载", on_click=self.load_current)
                ui.button("保存", color="primary", on_click=self.save_current)
                ui.button("删除", color="negative", on_click=self.delete_current)
            self.setup_footer()

    def clear_selection(self) -> None:
        self.select.value = None
        self.name_input.value = ""
        self.fill_template()
        self.selected_name["value"] = ""

    def setup_toolbar(self):
        """Override to add more buttons to the top toolbar"""
        pass

    def setup_footer(self):
        """Override to add more buttons to the bottom footer"""
        pass

    def __call__(self, *args, **kwargs):
        self.refresh_options()

    def refresh_options(self) -> None:
        options = list_task_names(self.kind, state.workdir)
        self.select.options = options
        self.select.update()

    def load_current(self) -> None:
        target = self.select.value
        if not target:
            return
        try:
            entry = load_config(self.kind, target, workdir=state.workdir)
            self.editor.properties["content"]["json"] = entry.payload
            self.name_input.value = entry.name
            self.editor.update()
            self.name_input.update()
            self.editor.run_editor_method(":expand", "[]", "path => true")
            self.selected_name["value"] = target
            self.on_loaded(target)
        except Exception as exc:  # noqa: BLE001
            notify_error(exc)

    def on_loaded(self, target: str):
        """Hook called after config is loaded"""
        pass

    def save_current(self) -> None:
        target = (self.name_input.value or self.select.value or "").strip()
        if not target:
            ui.notify("请先填写配置名称", type="warning")
            return
        try:
            save_config(
                self.kind,
                target,
                self.editor.properties["content"]["json"] or "{}",
                workdir=state.workdir,
            )
            self.refresh_options()
            self.select.value = target
            self.select.update()
            ui.notify("保存成功", type="positive")
        except Exception as exc:  # noqa: BLE001
            notify_error(exc)

    def fill_template(self) -> None:
        self.editor.properties["content"]["json"] = self.template
        self.editor.update()

    def delete_current(self) -> None:
        target = (self.select.value or "").strip() or (
            self.name_input.value or ""
        ).strip()
        if not target:
            ui.notify("请选择要删除的配置", type="warning")
            return
        try:
            delete_config(self.kind, target, workdir=state.workdir)
            self.refresh_options()
            if self.select.value == target:
                self.select.value = None
                self.select.update()
            ui.notify("已删除配置", type="positive")
        except Exception as exc:  # noqa: BLE001
            notify_error(exc)


class SignerBlock(BaseConfigBlock):
    def __init__(
        self,
        template: Dict[str, object],
        *,
        goto_records: Callable[[str], None] = lambda _task: None,
    ):
        self.record_btn = None
        self.record_hint = None
        self._goto_records = goto_records
        super().__init__("signer", template)

    def setup_toolbar(self):
        ui.button("交互式配置", on_click=self.open_interactive).props("outline")

    def setup_footer(self):
        self.record_hint = ui.label("").classes("text-sm text-primary")
        self.record_btn = ui.button(
            "查看签到记录",
            color="primary",
            on_click=self.goto_records,
        ).classes("min-w-[120px]")
        self.record_btn.disable()

    def on_loaded(self, target: str):
        records = load_sign_records(state.workdir)
        has_record = any(r.task == target for r in records)
        if has_record:
            self.record_btn.enable()
            self.record_hint.text = f"发现签到记录: {target}"
        else:
            self.record_btn.disable()
            self.record_hint.text = "无签到记录"
        self.record_hint.update()
        self.record_btn.update()

    def goto_records(self):
        self._goto_records(self.selected_name["value"])

    def open_interactive(self):
        def on_complete():
            self.refresh_options()
            # If the user saved a config with the same name as currently selected, reload it
            if self.select.value:
                self.load_current()

        initial_config = self.editor.properties["content"].get("json")
        initial_name = self.name_input.value or self.select.value or ""

        wizard = InteractiveSignerConfig(
            state.workdir,
            on_complete=on_complete,
            initial_config=initial_config,
            initial_name=initial_name,
        )
        wizard.open()


class MonitorBlock(BaseConfigBlock):
    def __init__(self, template: Dict[str, object]):
        super().__init__("monitor", template)


def user_info_block() -> Callable[[], None]:
    container = ui.column().classes("w-full gap-2")

    def refresh() -> None:
        container.clear()
        entries = load_user_infos(state.workdir)
        with container:
            if not entries:
                ui.label("未找到用户信息").classes("text-gray-500")
                return
            for entry in entries:
                name = entry.data.get("first_name") or ""
                header = f"{entry.user_id} {name}".strip()
                with ui.expansion(header, icon="person"):
                    ui.label(f"文件: {entry.path}")
                    ui.code(pretty_json(entry.data), language="json").classes("w-full")

                    if entry.latest_chats:
                        ui.separator().classes("my-2")
                        ui.label(f"最近聊天 ({len(entry.latest_chats)})").classes(
                            "font-semibold"
                        )

                        chat_rows = []
                        for chat in entry.latest_chats:
                            chat_rows.append(
                                {
                                    "id": chat.get("id"),
                                    "title": chat.get("title")
                                    or chat.get("first_name")
                                    or "N/A",
                                    "type": chat.get("type"),
                                    "username": chat.get("username") or "",
                                }
                            )

                        ui.table(
                            columns=[
                                {
                                    "name": "id",
                                    "label": "ID",
                                    "field": "id",
                                    "align": "left",
                                },
                                {
                                    "name": "title",
                                    "label": "名称",
                                    "field": "title",
                                    "align": "left",
                                },
                                {
                                    "name": "type",
                                    "label": "类型",
                                    "field": "type",
                                    "align": "left",
                                },
                                {
                                    "name": "username",
                                    "label": "用户名",
                                    "field": "username",
                                    "align": "left",
                                },
                            ],
                            rows=chat_rows,
                            pagination=10,
                        ).classes("w-full").props("flat dense")
                    else:
                        ui.label("未找到最近聊天记录").classes(
                            "text-gray-500 text-sm mt-2"
                        )

    return refresh


class SignRecordBlock:
    def __init__(self):
        self.container = ui.column().classes("w-full gap-3")
        with ui.row().classes("items-end gap-3"):
            self.filter_input = ui.input(
                label="筛选任务/用户",
                placeholder="输入任务名或用户ID过滤",
                value=state.record_filter,
                on_change=lambda e: self._update_filter(e.value),
            ).classes("w-full")
            ui.button("清除筛选", on_click=lambda: self._update_filter("")).props(
                "outline"
            )
        self.status = ui.label("").classes("text-sm text-gray-500")

    def _update_filter(self, value: str) -> None:
        state.record_filter = value or ""
        self.refresh()

    def refresh(
        self,
    ) -> None:
        self.container.clear()
        records = load_sign_records(state.workdir)
        keyword = (state.record_filter or "").lower().strip()
        if keyword:
            records = [
                r
                for r in records
                if keyword in r.task.lower()
                or (r.user_id and keyword in str(r.user_id).lower())
            ]
        with self.container:
            if not records:
                self.status.text = "未找到匹配的签到记录" if keyword else "尚无签到记录"
                self.status.update()
                return
            self.status.text = f"共 {len(records)} 组记录"
            self.status.update()
            for record in records:
                user_text = record.user_id or "默认"
                header = f"{record.task} / {user_text}（{len(record.records)}条）"
                with ui.expansion(header, icon="event").classes("shadow-sm"):
                    ui.label(f"文件: {record.path}").classes("text-gray-500")
                    if not record.records:
                        ui.label("暂无记录").classes("text-gray-500")
                        continue
                    rows = [{"日期": k, "时间": v} for k, v in record.records]
                    ui.table(
                        columns=[
                            {"name": "日期", "label": "日期", "field": "日期"},
                            {"name": "时间", "label": "时间", "field": "时间"},
                        ],
                        rows=rows,
                    ).classes("w-full").props("flat dense")

    def __call__(self, *args, **kwargs):
        return self.refresh()


def log_block() -> Callable[[], None]:
    with ui.card().classes("w-full shadow-sm"):
        ui.label("日志查看").classes("text-md font-semibold")
        ui.label("查看最新日志行，可自定义文件路径和行数。").classes(
            "text-sm text-gray-500 mb-1"
        )

        with ui.row().classes("items-end w-full gap-3 flex-wrap"):
            limit_input = ui.number(
                label="日志行数",
                value=state.log_limit,
                min=10,
                max=2000,
                format="%d",
            ).classes("w-32")
            log_select = ui.select(
                label=f"选择日志文件（{LOG_DIR}/）",
                options=[],
                on_change=lambda e: select_log_file(e.value),
            ).classes("min-w-[220px]")
            log_path_input = ui.input(
                label="日志路径（可自定义）", value=str(state.log_path)
            ).classes("w-full")
        log_area = ui.scroll_area().classes(
            "w-full bg-gray-50 rounded-lg border border-gray-200"
        )
        log_area.style("max-height: 420px")
        with log_area:
            log_list = (
                ui.column()
                .classes("w-full gap-0 p-3 font-mono text-sm")
                .style("white-space: pre;")
            )

        def classify_line(line: str) -> str:
            upper = line.upper()
            if "ERROR" in upper:
                return "text-red-700"
            if "WARN" in upper:
                return "text-amber-700"
            if "INFO" in upper:
                return "text-blue-700"
            return "text-gray-800"

        def refresh_log_options() -> None:
            options = [str(p) for p in list_log_files(LOG_DIR)]
            current_path = str(log_path_input.value or state.log_path)
            if current_path and current_path not in options:
                options.insert(0, current_path)
            log_select.options = options
            log_select.value = current_path
            log_select.update()

        def select_log_file(path_value: str | None) -> None:
            if not path_value:
                return
            log_path_input.value = path_value
            log_path_input.update()
            refresh()

        def refresh() -> None:
            refresh_log_options()
            try:
                state.log_limit = int(limit_input.value or state.log_limit)
            except ValueError:
                state.log_limit = 200
            state.set_log_path(log_path_input.value or str(DEFAULT_LOG_FILE))
            path, lines = load_logs(state.log_limit, log_path_input.value)
            log_list.clear()
            if not lines:
                with log_list:
                    ui.label(f"未找到日志文件: {path}").classes("text-gray-500 text-sm")
                log_list.update()
                refresh_status(f"未找到日志文件: {path}")
                return

            with log_list:
                for line in lines:
                    color = classify_line(line)
                    ui.label(line).classes(f"w-full {color}").style("white-space: pre;")
            log_list.update()
            refresh_status(f"文件: {path} | 显示最新 {len(lines)} 行")

        with ui.row().classes("gap-2 mt-2 items-center justify-between"):
            ui.button("刷新日志", on_click=refresh)
            log_status = ui.label("").classes("text-xs text-gray-500")

        def refresh_status(text: str) -> None:
            log_status.text = text
            log_status.update()

        refresh_log_options()

    return refresh


def top_controls(on_refresh: Callable[[], None]) -> None:
    with ui.card().classes("w-full"):
        ui.label("基础设置").classes("text-lg font-semibold")
        with ui.row().classes("items-end w-full"):
            workdir_input = ui.input(
                label="工作目录",
                value=str(state.workdir),
                placeholder=".signer",
            ).classes("w-full")
            ui.button(
                "应用并刷新",
                color="primary",
                on_click=lambda: _apply_paths(workdir_input, on_refresh),
            )


def _apply_paths(workdir_input, on_refresh: Callable[[], None]) -> None:
    try:
        state.set_workdir(workdir_input.value or str(DEFAULT_WORKDIR))
        ui.notify(f"已切换工作目录: {state.workdir}", type="positive")
    except Exception as exc:  # noqa: BLE001
        notify_error(exc)
        return
    on_refresh()


def _build_dashboard(container) -> None:
    with container:
        ui.label("TG Signer Web 控制台").classes(
            "text-2xl font-semibold tracking-wide mb-2"
        )
        refreshers: list[Callable[[], None]] = []
        refresh_records: "SignRecordBlock"

        def refresh_all() -> None:
            for refresh in refreshers:
                refresh()

        top_controls(refresh_all)

        with ui.tabs().classes("w-full") as tabs:
            tab_configs = ui.tab("配置管理")
            tab_users = ui.tab("用户信息")
            tab_records = ui.tab("签到记录")
            tab_logs = ui.tab("日志")

        def goto_records(task_name: str) -> None:
            tabs.value = tab_records
            tabs.update()
            refresh_records.filter_input.set_value(task_name)

        with ui.tab_panels(tabs, value=tab_configs).classes("w-full"):
            with ui.tab_panel(tab_configs):
                ui.label(
                    "管理 signer 和 monitor 的配置文件，支持查看、编辑和删除。"
                ).classes("text-gray-600")
                with ui.tabs().classes("mt-2") as sub_tabs:
                    tab_signer = ui.tab("Signer")
                    tab_monitor = ui.tab("Monitor")
                with ui.tab_panels(sub_tabs, value=tab_signer).classes("w-full"):
                    with ui.tab_panel(tab_signer):
                        refreshers.append(
                            SignerBlock(SIGNER_TEMPLATE, goto_records=goto_records)
                        )
                    with ui.tab_panel(tab_monitor):
                        refreshers.append(MonitorBlock(MONITOR_TEMPLATE))

            with ui.tab_panel(tab_users):
                ui.label("查看当前已登录账户信息 (users/*/me.json)。").classes(
                    "text-gray-600"
                )
                refreshers.append(user_info_block())

            with ui.tab_panel(tab_records):
                ui.label("签到记录 sign_record.json").classes("text-gray-600")
                refresh_records = SignRecordBlock()
                refreshers.append(refresh_records)

            with ui.tab_panel(tab_logs):
                ui.label("查看日志文件的最新行。").classes("text-gray-600")
                refreshers.append(log_block())

        refresh_all()


def _auth_gate(container, auth_code: str, on_success: Callable[[], None]) -> None:
    with container:
        ui.label("TG Signer Web 控制台").classes(
            "text-2xl font-semibold tracking-wide mb-2"
        )
        ui.label("已启用访问控制，请输入 Auth Code 继续使用 Web 控制台。").classes(
            "text-gray-600"
        )
        with ui.column().classes("w-full items-center"):
            with ui.card().classes("w-full max-w-xl shadow-md"):
                ui.label("Auth Code 验证").classes("text-lg font-semibold")
                ui.label("检测到auth_code环境变量已配置，首次访问需验证。").classes(
                    "text-sm text-gray-500"
                )
                code_input = ui.input(
                    label="Auth Code",
                    placeholder="请输入授权码",
                    password=True,
                    password_toggle_button=True,
                ).classes("w-full")
                status = ui.label("").classes("text-sm text-negative")

                def verify() -> None:
                    # TODO: Security improvements needed
                    # 1. Add rate limiting (e.g. max 5 attempts per minute) to prevent brute-force attacks.
                    # 2. Use secrets.compare_digest(code, auth_code) to prevent timing attacks.
                    code = (code_input.value or "").strip()
                    if not code:
                        ui.notify("请输入授权码", type="warning")
                        return
                    if code != auth_code:
                        status.text = "授权码错误，请重试"
                        status.update()
                        code_input.set_value("")
                        ui.notify("认证失败", type="negative")
                        return
                    app.storage.user[AUTH_STORAGE_KEY] = auth_code
                    ui.notify("认证成功", type="positive")
                    container.clear()
                    on_success()

                ui.button("验证并进入", color="primary", on_click=verify).classes(
                    "w-full mt-2"
                )


def build_ui(auth_code: str = None) -> None:
    ui.page_title("TG Signer Web 控制台")
    root = ui.column().classes("w-full gap-3")

    def render_dashboard() -> None:
        root.clear()
        _build_dashboard(root)

    auth_code = auth_code or (os.environ.get(AUTH_CODE_ENV) or "").strip()
    if not auth_code:
        render_dashboard()
        return

    if app.storage.user.get(AUTH_STORAGE_KEY) == auth_code:
        render_dashboard()
        return

    root.clear()
    _auth_gate(root, auth_code, render_dashboard)


def main(host: str = None, port: int = None, storage_secret: str = None) -> None:
    ui.run(
        build_ui,
        title="TG Signer WebUI",
        favicon="⚙️",
        reload=False,
        host=host,
        port=port,
        show=False,
        storage_secret=storage_secret or os.urandom(10).hex(),
    )
