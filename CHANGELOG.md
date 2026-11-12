# Changelog / 版本变动日志

## 版本变动日志

### 未发布

- 固定依赖 `kurigram==2.2.27`，适配新版事件循环接口，修复登录和任务启动失败的问题（#145）
- 使用 `ForumTopic.name` 输出话题名称，修复登录和查询话题时的字段访问错误
- 修复登出时客户端尚未初始化导致会话无法清理的问题
- 保留省略端口的代理配置，SOCKS4/5 默认使用 `1080`，HTTP 默认使用 `8080`

### 0.9.0
- 新增 `list-folders` 和 `--from-folder`，支持从 Telegram 普通对话 Folder 加载手动添加的对话
- 兼容 Kurigram 同步与异步论坛话题解析接口
- 修复连续动作处理中已消费消息占位导致 `wait_for` 崩溃的问题
- `根据图片选择选项` 动作支持图片与 InlineKeyboard 按钮分离的验证码场景
- 将版本变动日志从 README 移至独立的 `CHANGELOG.md`
- 监控配置支持 `send_text_template`，可将正则捕获结果或消息文本渲染到自动回复内容中
- 修复图片消息中的计算题无法识别 `caption` 的问题
- `回复计算题` 动作在存在 InlineKeyboard 选项时，会将按钮选项传给大模型并点击匹配按钮
- `根据图片选择选项` 动作会将消息文本或 `caption` 作为图片识别问题，并校验大模型返回的选项序号

### 0.8.6
- 支持 Telegram 论坛群组话题 `message_thread_id`
- 登录时可发现群组话题，新增 `list-topics` 用于查询话题 ID
- `send-text`、`send-dice`、`schedule-messages`、签到配置与 WebUI 支持发送到指定话题
- 签到记录迁移到 SQLite，新增 `list-sign-records` 与 `migrate-sign-records`
- 兼容读取旧版 `sign_record.json`，运行任务时可自动导入历史记录
- 发布官方 GHCR 镜像：`ghcr.io/amchii/tg-signer:<tag>` 与 `ghcr.io/amchii/tg-signer:<tag>-webui`
- 改进论坛群组、频道私信等场景下的话题发现与消息发送兼容性

### 0.8.5
- `kurigram>=2.2.19,<2.3.0`
- 单账户多任务时进行并发请求限流

### 0.8.4
- 新增 WebGUI
- 新增 `--log-dir` 选项，更改日志默认目录为 `logs`，warning 和 error 分为单独文件

### 0.8.2
- 支持持久化 OpenAI API 和模型配置
- Python 最小版本要求：3.10
- 支持处理编辑后的消息（如键盘）

### 0.8.0
- 支持单个账号同一进程内同时运行多个任务

### 0.7.6
- fix: 监控多个聊天时消息转发至每个聊天 (#55)

### 0.7.5
- 捕获并记录执行任务期间的所有 RPC 错误
- bump kurigram version to 2.2.7

### 0.7.4
- 执行多个 action 时，支持固定时间间隔
- 通过 `crontab` 配置定时执行时不再限制每日执行一次

### 0.7.2
- 支持将消息转发至外部端点，通过：
  - UDP
  - HTTP
- 将 kurirogram 替换为 kurigram

### 0.7.0
- 支持每个聊天会话按序执行多个动作，动作类型：
  - 发送文本
  - 发送骰子
  - 按文本点击键盘
  - 通过图片选择选项
  - 通过计算题回复

### 0.6.6
- 增加对发送 DICE 消息的支持

### 0.6.5
- 修复使用同一套配置运行多个账号时签到记录共用的问题

### 0.6.4
- 增加对简单计算题的支持
- 改进签到配置和消息处理

### 0.6.3
- 兼容 kurigram 2.1.38 版本的破坏性变更
> Remove coroutine param from run method [a7afa32](https://github.com/KurimuzonAkuma/pyrogram/commit/a7afa32df208333eecdf298b2696a2da507bde95)

### 0.6.2
- 忽略签到时发送消息失败的聊天

### 0.6.1
- 支持点击按钮文本后继续进行图片识别

### 0.6.0
- Signer 支持通过 crontab 定时
- Monitor 匹配规则添加 `all` 支持所有消息
- Monitor 支持匹配到消息后通过 server 酱推送
- Signer 新增 `multi-run` 用于使用一套配置同时运行多个账号

### 0.5.2
- Monitor 支持配置 AI 进行消息回复
- 增加批量配置「Telegram 自带的定时发送消息功能」的功能

### 0.5.1
- 添加 `import` 和 `export` 命令用于导入导出配置

### 0.5.0
- 根据配置的文本点击键盘
- 调用 AI 识别图片点击键盘

## Changelog

### Unreleased

- Pin `kurigram==2.2.27` and adapt to its event loop changes to fix login and task startup failures (#145).
- Read topic names from `ForumTopic.name` to fix topic output during login and topic queries.
- Initialize the connected client before logout so session cleanup can complete.
- Preserve proxy URLs without an explicit port by defaulting SOCKS4/5 to `1080` and HTTP to `8080`.

### 0.9.0
- Add `list-folders` and `--from-folder` to load manually added chats from regular Telegram folders
- Support both synchronous and asynchronous Kurigram forum topic parsers
- Fix `wait_for` crashes caused by consumed message placeholders during multi-action flows
- Support captcha flows where the image and InlineKeyboard buttons are sent as separate messages for `ChooseOptionByImageAction`
- Move the changelog out of README files and into standalone `CHANGELOG.md`
- Add `send_text_template` support for monitor configs, allowing regex captures or message text to be rendered into automatic replies
- Fix calculation questions in image messages not being detected from `caption`
- When `ReplyByCalculationProblemAction` sees InlineKeyboard options, pass those options to the LLM and click the matching button
- Pass message text or `caption` as the image-recognition question for `ChooseOptionByImageAction`, and validate the returned option index

### 0.8.6
- Support Telegram forum group topics via `message_thread_id`
- Discover group topics during login, and add `list-topics` for querying topic IDs
- `send-text`, `send-dice`, `schedule-messages`, check-in configuration, and WebUI now support sending to a specific topic
- Migrate check-in records to SQLite, and add `list-sign-records` plus `migrate-sign-records`
- Keep compatibility for reading the old `sign_record.json`, and auto-import legacy records when running tasks
- Publish official GHCR images: `ghcr.io/amchii/tg-signer:<tag>` and `ghcr.io/amchii/tg-signer:<tag>-webui`
- Improve compatibility for topic discovery and message delivery in forum groups, channel DMs, and similar scenarios

### 0.8.5
- `kurigram>=2.2.19,<2.3.0`
- Add concurrent request throttling when multiple tasks run under a single account

### 0.8.4
- Add WebGUI
- Add the `--log-dir` option, change the default log directory to `logs`, and split warning and error logs into separate files

### 0.8.2
- Support persistent OpenAI API and model configuration
- Minimum supported Python version is now 3.10
- Support handling edited messages (for example, updated keyboards)

### 0.8.0
- Support running multiple tasks in the same process for a single account

### 0.7.6
- Fix: when monitoring multiple chats, forwarded messages are delivered to each target chat correctly (#55)

### 0.7.5
- Capture and log all RPC errors during task execution
- Bump kurigram to version 2.2.7

### 0.7.4
- Support fixed intervals when executing multiple actions
- Remove the once-per-day limitation when scheduling with `crontab`

### 0.7.2
- Support forwarding messages to external endpoints through:
  - UDP
  - HTTP
- Replace kurirogram with kurigram

### 0.7.0
- Support executing multiple actions sequentially for each chat session. Supported action types:
  - Send text
  - Send dice
  - Click a keyboard button by text
  - Select an option by image
  - Reply to a math question

### 0.6.6
- Add support for sending DICE messages

### 0.6.5
- Fix shared check-in records when multiple accounts run with the same configuration

### 0.6.4
- Add support for simple math questions
- Improve check-in configuration and message handling

### 0.6.3
- Compatible with the breaking change introduced in kurigram 2.1.38
> Remove coroutine param from run method [a7afa32](https://github.com/KurimuzonAkuma/pyrogram/commit/a7afa32df208333eecdf298b2696a2da507bde95)

### 0.6.2
- Ignore chats where sending a check-in message fails

### 0.6.1
- Support continuing with image recognition after clicking a button by text

### 0.6.0
- Add crontab scheduling to Signer
- Add the `all` rule to Monitor for matching all messages
- Add ServerChan push support for Monitor
- Add `multi-run` so multiple accounts can run with one shared configuration

### 0.5.2
- Monitor supports AI-based replies
- Add batch configuration for Telegram's built-in scheduled messages

### 0.5.1
- Add `import` and `export` commands for configuration import/export

### 0.5.0
- Click keyboard buttons based on configured text
- Use AI to recognize images and click keyboard buttons
