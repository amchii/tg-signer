const state = {
  tasks: [],
  actions: [],
  actionMap: new Map(),
  activeTask: null,
  config: null,
  dirty: false,
};

const ACTION_FIELD_CONFIG_BY_KEY = {
  SEND_TEXT: { field: "text", label: "发送内容", placeholder: "例如：今天也要开心~" },
  SEND_DICE: { field: "dice", label: "骰子/Emoji", placeholder: "🎲" },
  CLICK_KEYBOARD_BY_TEXT: {
    field: "text",
    label: "按钮文本",
    placeholder: "与按钮完全一致的文字",
  },
};

const elements = {
  createButton: document.getElementById("create-task"),
  saveButton: document.getElementById("save-task"),
  deleteButton: document.getElementById("delete-task"),
  taskList: document.getElementById("task-list"),
  statusArea: document.getElementById("status-area"),
  workspaceTitle: document.getElementById("workspace-title"),
  workspaceSubtitle: document.getElementById("workspace-subtitle"),
  editor: document.getElementById("editor"),
  emptyState: document.getElementById("empty-state"),
};

init();

async function init() {
  bindEvents();
  await loadActions();
  await refreshTasks();
}

function bindEvents() {
  elements.createButton.addEventListener("click", onCreateTask);
  elements.saveButton.addEventListener("click", onSaveTask);
  elements.deleteButton.addEventListener("click", onDeleteTask);
}

async function loadActions() {
  try {
    const data = await requestJson("/api/meta/actions");
    state.actions = data.actions;
    state.actionMap.clear();
    state.actions.forEach((action) => {
      state.actionMap.set(Number(action.value), action);
    });
  } catch (error) {
    showStatus("error", `加载动作列表失败：${error.message}`);
  }
}

async function refreshTasks() {
  try {
    const data = await requestJson("/api/sign/tasks");
    state.tasks = data.tasks || [];
    renderTaskList();
    if (state.activeTask) {
      const stillExists = state.tasks.some((task) => task.name === state.activeTask);
      if (stillExists) {
        await loadTask(state.activeTask);
      } else {
        setActiveTask(null);
      }
    }
  } catch (error) {
    showStatus("error", `读取策略列表失败：${error.message}`);
  }
}

function renderTaskList() {
  elements.taskList.innerHTML = "";
  if (!state.tasks.length) {
    const hint = document.createElement("div");
    hint.className = "task-empty";
    hint.textContent = "暂无策略";
    elements.taskList.appendChild(hint);
    return;
  }
  state.tasks.forEach((task) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "task-item";
    item.dataset.name = task.name;
    item.textContent = task.name;
    if (state.activeTask === task.name) {
      item.classList.add("active");
    }
    item.addEventListener("click", () => loadTask(task.name));
    elements.taskList.appendChild(item);
  });
}

async function loadTask(name) {
  try {
    const data = await requestJson(`/api/sign/tasks/${encodeURIComponent(name)}`);
    setActiveTask(data.name, data.config);
    showStatus("success", `已载入策略「${data.name}」`);
  } catch (error) {
    showStatus("error", `无法读取策略：${error.message}`);
  }
}

function setActiveTask(name, config = null) {
  state.activeTask = name;
  state.config = config;
  setDirty(false);
  renderTaskList();
  updateWorkspaceHeader();
  renderEditor();
}

function updateWorkspaceHeader() {
  if (state.activeTask) {
    elements.workspaceTitle.textContent = `策略：${state.activeTask}`;
    elements.workspaceSubtitle.textContent = "在此页面编辑签到流程、动作与时间安排";
    elements.saveButton.disabled = !state.dirty;
    elements.deleteButton.disabled = false;
  } else {
    elements.workspaceTitle.textContent = "策略详情";
    elements.workspaceSubtitle.textContent = "选择或新建一个策略，开始可视化配置流程";
    elements.saveButton.disabled = true;
    elements.deleteButton.disabled = true;
  }
}

function renderEditor() {
  elements.editor.innerHTML = "";
  if (!state.config) {
    elements.editor.appendChild(elements.emptyState);
    elements.emptyState.classList.remove("hidden");
    return;
  }
  elements.emptyState.classList.add("hidden");

  const generalSection = document.createElement("section");
  generalSection.className = "form-section";
  const generalTitle = document.createElement("h2");
  generalTitle.textContent = "基础设置";
  generalSection.appendChild(generalTitle);

  const generalGrid = document.createElement("div");
  generalGrid.className = "field-grid";
  generalGrid.appendChild(
    createField("签到时间", "text", state.config.sign_at || "", (value) => {
      state.config.sign_at = value.trim();
      setDirty(true);
    }, "例如 06:00:00 或 0 6 * * *")
  );
  generalGrid.appendChild(
    createField("随机延迟秒数", "number", state.config.random_seconds ?? 0, (value) => {
      state.config.random_seconds = parseInt(value, 10) || 0;
      setDirty(true);
    })
  );
  generalGrid.appendChild(
    createField("连续动作间隔秒数", "number", state.config.sign_interval ?? 1, (value) => {
      const parsed = parseFloat(value);
      state.config.sign_interval = Number.isFinite(parsed) ? parsed : 1;
      setDirty(true);
    })
  );
  generalSection.appendChild(generalGrid);
  elements.editor.appendChild(generalSection);

  const chatsSection = document.createElement("section");
  chatsSection.className = "form-section";
  const chatsTitle = document.createElement("h2");
  chatsTitle.textContent = "签到聊天";
  chatsSection.appendChild(chatsTitle);

  if (!Array.isArray(state.config.chats)) {
    state.config.chats = [];
  }

  state.config.chats.forEach((chat, index) => {
    chatsSection.appendChild(renderChatEditor(chat, index));
  });

  const inlineActions = document.createElement("div");
  inlineActions.className = "inline-actions";
  const addChatButton = document.createElement("button");
  addChatButton.type = "button";
  addChatButton.className = "primary";
  addChatButton.textContent = "新增聊天";
  addChatButton.addEventListener("click", () => {
    addChat();
  });
  inlineActions.appendChild(addChatButton);
  chatsSection.appendChild(inlineActions);

  elements.editor.appendChild(chatsSection);
}

function renderChatEditor(chat, index) {
  const container = document.createElement("section");
  container.className = "chat-editor";

  const header = document.createElement("div");
  header.className = "chat-header";
  const title = document.createElement("h3");
  title.textContent = `聊天 ${index + 1}`;
  header.appendChild(title);
  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "ghost";
  removeButton.textContent = "删除";
  removeButton.addEventListener("click", () => {
    if (state.config.chats.length <= 1) {
      showStatus("error", "至少需要保留一个聊天配置");
      return;
    }
    state.config.chats.splice(index, 1);
    setDirty(true);
    renderEditor();
  });
  header.appendChild(removeButton);
  container.appendChild(header);

  const grid = document.createElement("div");
  grid.className = "field-grid";
  grid.appendChild(
    createField("Chat ID", "number", chat.chat_id ?? "", (value) => {
      const parsed = Number(value);
      chat.chat_id = Number.isFinite(parsed) ? parsed : null;
      setDirty(true);
    })
  );
  grid.appendChild(
    createField("备注名称", "text", chat.name ?? "", (value) => {
      chat.name = value.trim();
      setDirty(true);
    })
  );
  grid.appendChild(
    createField("删除延时（秒）", "number", chat.delete_after ?? "", (value) => {
      if (value === "") {
        chat.delete_after = null;
      } else {
        const parsed = parseInt(value, 10);
        chat.delete_after = Number.isFinite(parsed) ? parsed : null;
      }
      setDirty(true);
    }, "留空表示不删除")
  );
  grid.appendChild(
    createField("动作间隔（秒）", "number", chat.action_interval ?? 1, (value) => {
      const parsed = parseFloat(value);
      chat.action_interval = Number.isFinite(parsed) ? parsed : 1;
      setDirty(true);
    })
  );
  container.appendChild(grid);

  const actionsTitle = document.createElement("h4");
  actionsTitle.textContent = "动作流程";
  container.appendChild(actionsTitle);

  if (!Array.isArray(chat.actions)) {
    chat.actions = [];
  }
  const actionList = document.createElement("div");
  actionList.className = "action-list";
  chat.actions.forEach((action, actionIndex) => {
    actionList.appendChild(renderActionRow(chat, action, actionIndex));
  });
  container.appendChild(actionList);

  const addActionButton = document.createElement("button");
  addActionButton.type = "button";
  addActionButton.textContent = "新增动作";
  addActionButton.className = "primary";
  addActionButton.addEventListener("click", () => {
    addAction(chat);
  });
  container.appendChild(addActionButton);

  return container;
}

function renderActionRow(chat, action, index) {
  const row = document.createElement("div");
  row.className = "action-row";

  const typeField = document.createElement("div");
  typeField.className = "field";
  const typeLabel = document.createElement("label");
  typeLabel.textContent = "动作类型";
  typeField.appendChild(typeLabel);
  const select = document.createElement("select");
  state.actions.forEach((meta) => {
    const option = document.createElement("option");
    option.value = String(meta.value);
    option.textContent = meta.label;
    select.appendChild(option);
  });
  select.value = String(action.action ?? state.actions[0]?.value ?? "");
  select.addEventListener("change", (event) => {
    const nextValue = Number(event.target.value);
    updateActionType(chat, action, nextValue);
  });
  typeField.appendChild(select);
  row.appendChild(typeField);

  const currentMeta = state.actionMap.get(Number(select.value));
  const fieldConfig = currentMeta
    ? ACTION_FIELD_CONFIG_BY_KEY[currentMeta.key] || null
    : null;

  const valueField = document.createElement("div");
  valueField.className = "field";
  if (fieldConfig) {
    const label = document.createElement("label");
    label.textContent = fieldConfig.label;
    valueField.appendChild(label);
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = fieldConfig.placeholder || "";
    const key = fieldConfig.field;
    input.value = action[key] ?? "";
    input.addEventListener("input", (event) => {
      action[key] = event.target.value;
      setDirty(true);
    });
    valueField.appendChild(input);
  }
  row.appendChild(valueField);

  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "ghost";
  deleteButton.textContent = "移除";
  deleteButton.addEventListener("click", () => {
    if (chat.actions.length <= 1) {
      showStatus("error", "每个聊天至少需要一个动作");
      return;
    }
    chat.actions.splice(index, 1);
    setDirty(true);
    renderEditor();
  });
  row.appendChild(deleteButton);

  return row;
}

function createField(labelText, type, value, onChange, placeholder = "") {
  const field = document.createElement("div");
  field.className = "field";
  const label = document.createElement("label");
  label.textContent = labelText;
  field.appendChild(label);
  const input = document.createElement(type === "textarea" ? "textarea" : "input");
  if (type !== "textarea") {
    input.type = type;
  }
  if (value !== undefined && value !== null) {
    input.value = value;
  }
  if (placeholder) {
    input.placeholder = placeholder;
  }
  input.addEventListener("input", (event) => onChange(event.target.value));
  field.appendChild(input);
  return field;
}

function addChat() {
  const defaultAction = state.actions.find((item) => item.key === "SEND_TEXT");
  const action = defaultAction
    ? { action: Number(defaultAction.value), text: "" }
    : { action: state.actions[0]?.value ?? 1 };
  state.config.chats.push({
    chat_id: null,
    name: "",
    delete_after: null,
    action_interval: 1,
    actions: [action],
  });
  setDirty(true);
  renderEditor();
}

function addAction(chat) {
  const defaultAction = state.actions.find((item) => item.key === "SEND_TEXT");
  const action = defaultAction
    ? { action: Number(defaultAction.value), text: "" }
    : { action: state.actions[0]?.value ?? 1 };
  chat.actions.push(action);
  setDirty(true);
  renderEditor();
}

function updateActionType(chat, action, nextValue) {
  action.action = Number(nextValue);
  const meta = state.actionMap.get(action.action);
  const config = meta ? ACTION_FIELD_CONFIG_BY_KEY[meta.key] : null;
  if (!config) {
    delete action.text;
    delete action.dice;
  } else {
    const key = config.field;
    if (action[key] === undefined) {
      action[key] = "";
    }
    if (config.field === "dice" && !action[key]) {
      action[key] = "🎲";
    }
  }
  setDirty(true);
  renderEditor();
}

async function onCreateTask() {
  const name = window.prompt("请输入新的策略名称", "my_sign_task");
  if (!name) {
    return;
  }
  try {
    const data = await requestJson("/api/sign/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    showStatus("success", `策略「${data.name}」已创建`);
    await refreshTasks();
    await loadTask(data.name);
  } catch (error) {
    showStatus("error", `创建失败：${error.message}`);
  }
}

async function onSaveTask() {
  if (!state.activeTask || !state.config) {
    return;
  }
  try {
    await requestJson(`/api/sign/tasks/${encodeURIComponent(state.activeTask)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: state.config }),
    });
    showStatus("success", "保存成功");
    setDirty(false);
  } catch (error) {
    if (error.details) {
      const message = Array.isArray(error.details)
        ? error.details
            .map((item) => `${item.loc?.join(".") || "配置"}: ${item.msg}`)
            .join("；")
        : error.details;
      showStatus("error", `保存失败：${message}`);
    } else {
      showStatus("error", `保存失败：${error.message}`);
    }
  }
}

async function onDeleteTask() {
  if (!state.activeTask) {
    return;
  }
  const confirmed = window.confirm(`确定要删除策略「${state.activeTask}」吗？`);
  if (!confirmed) {
    return;
  }
  try {
    await requestJson(`/api/sign/tasks/${encodeURIComponent(state.activeTask)}`, {
      method: "DELETE",
    });
    showStatus("success", "策略已删除");
    setActiveTask(null);
    await refreshTasks();
  } catch (error) {
    showStatus("error", `删除失败：${error.message}`);
  }
}

function setDirty(next) {
  state.dirty = Boolean(next);
  elements.saveButton.disabled = !state.dirty || !state.activeTask;
}

function showStatus(type, message) {
  const el = elements.statusArea;
  el.textContent = message;
  el.classList.remove("hidden", "success", "error");
  el.classList.add(type);
  clearTimeout(showStatus.timer);
  showStatus.timer = setTimeout(() => {
    el.classList.add("hidden");
  }, 4000);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (response.status === 204) {
    return null;
  }
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const error = new Error(data?.detail || response.statusText);
    if (data?.detail) {
      error.details = data.detail;
    }
    throw error;
  }
  return data;
}
