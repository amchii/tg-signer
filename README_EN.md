## Telegram Signer - Daily Automatic Sign-in for Telegram

### Installation

```
pip install -U tg-signer
```

Or to improve the speed of the program:

```
pip install "tg-signer[tgcrypto]"
```

### Usage

```
Usage: tg-signer <command> [task_name]
```

Available commands: `list`, `login`, `run`, `run_once`, `reconfig`

- `list`: List existing configurations
- `login`: Log in to your account (used to get the session)
- `run`: Run the sign-in task based on the configuration
- `run_once`: Run a one-time sign-in task based on the configuration
- `reconfig`: Reconfigure the settings

For example:

```
tg-signer run
tg-signer run my_sign  # Run the 'my_sign' task directly without prompts
tg-signer run_once my_sign  # Run the 'my_sign' task just once
tg-signer send_text 8671234001 /test  # Send the '/test' text to the chat with chat_id '8671234001'
```

### Configuring a Proxy (if needed)
`tg-signer` does not use the system proxy settings, but you can configure the proxy using the environment variable `TG_PROXY`.

For example:

```
export TG_PROXY=socks5://127.0.0.1:7890
```

### Running

```
tg-signer run
```

Follow the prompts for configuration. Data and configurations are stored in the `.signer` directory. After running `tree .signer`, you will see:

```
.signer
├── latest_chats.json  # Recently retrieved chats
├── me.json  # Personal information
└── signs
    └── openai  # Sign-in task name
        ├── config.json  # Sign-in configuration
        └── sign_record.json  # Sign-in record

3 directories, 4 files
```
