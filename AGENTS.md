# 仓库协作指南

## 交流与工作方式

- 默认根据沟通对象使用的语言进行交流和解释改动；对方明确指定语言时，遵循其要求。新增文档沿用目标文档或项目的语言约定，代码标识符沿用项目现有命名风格。
- 修改前先阅读相关实现、测试和文档，优先沿用现有结构，保持改动聚焦。
- 保留用户已有的修改，不擅自重置工作区、回滚无关文件或执行提交、推送、发布。
- 完成后简要说明改动内容、验证结果，以及尚未验证的部分。

## 项目概况

`tg-signer` 是 Telegram 自动化工具，提供定时签到、消息监控、转发、自动回复、规则引擎和可选 WebUI。

- Python 最低版本为 3.10；持续集成覆盖 3.10、3.11、3.12，新增代码需保持兼容。
- 命令行使用 Click，配置使用 Pydantic，Telegram 客户端依赖 Kurigram，但导入名仍为 `pyrogram`。
- WebUI 使用 NiceGUI，属于可选依赖；基础命令行功能应能在未安装 GUI 依赖时使用。
- 依赖和工具配置以 `pyproject.toml` 为准，测试矩阵见 `tox.ini` 和 `.github/workflows/test.yml`。

## 主要目录与文件

| 路径 | 职责 |
| --- | --- |
| `tg_signer/__main__.py` | `tg-signer` 命令入口 |
| `tg_signer/cli/` | 签到、监控、自动化等命令行接口 |
| `tg_signer/core.py` | 客户端管理、签到和监控核心逻辑 |
| `tg_signer/config.py` | 配置模型、校验及版本转换 |
| `tg_signer/automation/` | 自动化模型、规则引擎和处理器 |
| `tg_signer/sign_record_store.py` | 签到记录存储 |
| `tg_signer/_kurigram/` | Kurigram 扩展及兼容补丁 |
| `tg_signer/ai_tools.py` | 大模型调用相关逻辑 |
| `tg_signer/webui/` | WebUI 页面、交互及数据处理 |
| `tg_signer/notification/` | 通知渠道 |
| `tests/` | 自动化测试及离线 Telegram 测试设施 |
| `docs/` | 自动化规则设计与使用说明 |
| `docker/` | 镜像构建、部署配置及说明 |
| `README.md`、`README_EN.md` | 中文和英文使用说明 |

## 环境与常用命令

执行 Python 命令前，优先检查并使用仓库中的 `.venv` 或 `venv`，不要直接使用系统 Python。以下示例采用 `.venv`，若实际使用 `venv`，相应替换路径。

使用 uv 初始化或同步开发环境：

```sh
uv sync --group dev
# 需要开发 WebUI 或 YAML 配置功能时，按需安装可选依赖
uv sync --group dev --extra gui --extra yaml
```

常用检查命令：

```sh
# 静态检查
.venv/bin/python -m ruff check
# 格式检查；修改格式时仅对涉及的文件运行 ruff format
.venv/bin/python -m ruff format --check tg_signer/ tests/
# 完整测试，与持续集成的测试目录和警告过滤保持一致
.venv/bin/python -m pytest -W=ignore::DeprecationWarning:pyrogram.sync -vv tests/
# 针对性测试示例
.venv/bin/python -m pytest tests/test_automation_engine.py
```

按改动范围选择检查：纯文档修改核对内容和命令即可；代码修改先运行相关测试，涉及公共接口、配置迁移或客户端生命周期时运行完整测试。不要顺带格式化无关文件。

## 实现约定

- 保持实现简单直接，不要过度防御；依据明确需求和实际代码行为做设计，不凭假设增加业务限制、额外校验或复杂兜底。
- 使用四空格缩进，遵循现有类型注解和异步代码风格；Ruff 行宽配置为 88，具体检查规则以项目配置为准。
- 调整命令行参数时，检查 Click 定义、对应测试、帮助文本及文档示例，保留已有别名和兼容行为。
- 调整配置模型时，检查历史配置转换、默认值、序列化和 WebUI 的相关处理，避免破坏已有配置。
- 修改客户端或异步逻辑时，关注事件循环、客户端复用、锁、引用计数和资源释放，复用现有管理方式。
- 修改签到记录存储或迁移时，保持历史数据可读，并为迁移边界和重复执行行为提供验证。
- 新增自动化规则或处理器时，同时检查模型定义、处理器注册、引擎执行及对应使用说明。
- 修改公开用法时同步维护中英文 README；自动化功能的详细说明位于 `docs/automation_usage.md`。
- 仅在任务需要时修改依赖、版本号、发布配置或兼容补丁。

## 测试与本地数据

- 测试放在 `tests/` 下，沿用 `test_*.py` 命名；异步测试使用 pytest-asyncio。
- 优先复用 `tests/conftest.py` 中的 `signer_factory`、`telegram_server` 和 `tests/telegram.py` 中的测试对象，在临时目录中读写数据。
- Telegram 相关测试应使用离线设施或模拟网络边界；常规验证不应登录真实账号、发送真实消息或启动长期任务。
- 根目录的 `_test*.py` 属于本地脚本，不作为标准测试入口，不在未检查内容时批量执行。
- `.env`、`*.session`、`*.session_string`、`.signer/`、`.monitor/`、日志及本地数据库可能包含凭据或真实运行数据。不要为了了解项目而读取、输出、覆盖或提交这些内容；任务确需处理时限制范围，并对展示内容脱敏。
- 不修改虚拟环境、缓存、`*.egg-info/` 等生成内容来实现功能；应修改对应源码或配置。
