## Telegram Signer - Telegram每日自动签到
[English](./README_EN.md)

### 安装

```
pip install -U tg-signer
```

或者为了提升程序速度：

```
pip install "tg-signer[tgcrypto]"
```

### 使用方法

```
Usage: tg-signer <command> [task_name]
```

可用命令: `list`, `login`, `run`, `run_once`, `reconfig`

- `list`: 列出已有配置
- `login`: 登录账号（用于获取session）
- `run`: 根据配置运行签到
- `run_once`: 根据配置运行一次签到
- `reconfig`: 重新配置

例如:

```
tg-signer run
tg-signer run my_sign  # 不询问，直接运行'my_sign'任务
tg-signer run_once my_sign  # 直接运行一次'my_sign'任务
tg-signer send_text 8671234001 /test  # 向chat_id为'8671234001'的聊天发送'/test'文本
```

### 配置代理（如有需要）
`tg-signer`不读取系统代理，可以使用环境变量 `TG_PROXY`进行配置

例如：

```
export TG_PROXY=socks5://127.0.0.1:7890
```

### 运行

```
tg-signer run
```

根据提示进行配置。数据和配置保存在 `.signer` 目录中。然后运行 `tree .signer`，你将看到：

```
.signer
├── latest_chats.json  # 获取的最近对话
├── me.json  # 个人信息
└── signs
    └── openai  # 签到任务名
        ├── config.json  # 签到配置
        └── sign_record.json  # 签到记录

3 directories, 4 files
```
