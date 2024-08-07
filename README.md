# Telegram Signer - Telegram每日自动签到

## Install
```
pip install -U tg-signer
```
or for speedup:
```
pip install "tg-signer[tgcrypto]"
```

## Usage
```
Usage: tg-signer <command>
Available commands: list, login, run, run_once, reconfig
e.g. tg-signer run
e.g. tg-signer run_once [chat_id] [send_text]
```
#### Configure proxy(if necessary)
use env `TG_PROXY`

e.g.:
```
export TG_PROXY=socks5://127.0.0.1:7890
```

#### Run
`tg-signer run`

#### Run_Once
`tg-signer run_once [chat_id] [send_text]`

For a one-time sign-in, which can be used for crontab scheduled tasks.Before use `run_once`, you need to use `login` command to login telegram.

when you use `login`,you can get the `chat_id` you want. 

`send_text` is send to chat_id's content,like "/sign" 

---


Configure according to the prompts. The data and configuration are stored in the `.signer` directory.
Then run `tree .signer`, you will see:
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
