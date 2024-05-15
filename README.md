# Telegram Signer - Telegram每日自动签到

## Install
`pip install -U tg-signer`

## Usage
```
Usage: tg-signer <command>
Available commands: list, login, run, reconfig
e.g. tg-signer run
```

#### Run
`tg-signer run`

run `tree .signer` you will see:
```
.signer
├── latest_chats.json
├── me.json
└── signs
    └── aisgk  # 签到任务名
        ├── config.json  # 签到配置
        └── sign_record.json  # 签到记录

3 directories, 4 files
```
