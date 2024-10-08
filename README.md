## Telegram Signer - Telegram每日自动签到
[English](./README_EN.md)

### 安装

```
pip install -U tg-signer
```

或者为了提升程序速度：

```
pip install "tg-signer[speedup]"
```

### 使用方法

```
Usage: tg-signer [OPTIONS] COMMAND [ARGS]...

  使用<子命令> --help查看使用说明

子命令别名:
  run_once -> run-once
  send_text -> send-text

Options:
  -l, --log-level [debug|info|warn|error]
                                  日志等级, `debug`, `info`, `warn`, `error`
                                  [default: info]
  --log-file PATH                 日志文件路径, 可以是相对路径  [default: tg-signer.log]
  -p, --proxy TEXT                代理地址, 例如: socks5://127.0.0.1:1080,
                                  会覆盖环境变量`TG_PROXY`的值  [env var: TG_PROXY]
  --session_dir PATH              存储TG Sessions的目录, 可以是相对路径  [default: .]
  -a, --account TEXT              自定义账号名称，对应session文件名为<account>.session
                                  [default: my_account]
  --help                          Show this message and exit.

Commands:
  list       列出已有配置
  login      登录账号（用于获取session）
  logout     登出账号并删除session文件
  reconfig   重新配置
  run        根据任务配置运行签到
  run-once   运行一次签到任务，即使该签到任务今日已执行过
  send-text  发送一次消息, 请确保当前会话已经"见过"该`chat_id`
  version    Show version
```



例如:

```
tg-signer run
tg-signer run my_sign  # 不询问，直接运行'my_sign'任务
tg-signer run-once my_sign  # 直接运行一次'my_sign'任务
tg-signer send-text 8671234001 /test  # 向chat_id为'8671234001'的聊天发送'/test'文本
```

### 配置代理（如有需要）
`tg-signer`不读取系统代理，可以使用环境变量 `TG_PROXY`或命令参数`--proxy`进行配置

例如：

```
export TG_PROXY=socks5://127.0.0.1:7890
```

### 登录

```
tg-signer login
```

根据提示输入手机号码和验证码进行登录并获取最近的聊天列表，确保你想要签到的聊天在列表内。

### 运行签到任务

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

### 发送一次消息

```
tg-signer send-text 8671234001 hello  # 向chat_id为'8671234001'的聊天发送'hello'文本
```
