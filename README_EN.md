## Telegram Signer - Automatic Daily Check-in for Telegram

[中文](./README.md)

### Installation

```
pip install -U tg-signer
```

Or, to improve the speed of the program:

```
pip install "tg-signer[speedup]"
```

### Usage

```
Usage: tg-signer [OPTIONS] COMMAND [ARGS]...

  Use <subcommand> --help for detailed usage instructions.

Subcommand Aliases:
  run_once -> run-once
  send_text -> send-text

Options:
  -l, --log-level [debug|info|warn|error]
                                  Log level: `debug`, `info`, `warn`, `error`
                                  [default: info]
  --log-file PATH                 Path to log file, can be relative  [default: tg-signer.log]
  -p, --proxy TEXT                Proxy address, e.g., socks5://127.0.0.1:1080,
                                  will override the environment variable `TG_PROXY`  [env var: TG_PROXY]
  --session_dir PATH              Directory to store TG sessions, can be relative  [default: .]
  -a, --account TEXT              Custom account name, the corresponding session file is named <account>.session
                                  [default: my_account]
  --help                          Show this message and exit.

Commands:
  list       List existing configurations
  login      Login to account (to obtain session)
  logout     Logout from account and delete session file
  reconfig   Reconfigure settings
  run        Run check-in based on task configuration
  run-once   Execute a check-in task once, even if it has already been run today
  send-text  Send a message, make sure the current session has previously "seen" the `chat_id`
  version    Show version information
```

For example:

```
tg-signer run
tg-signer run my_sign  # Run the 'my_sign' task directly without asking
tg-signer run-once my_sign  # Run the 'my_sign' task once, regardless of whether it has already been executed today
tg-signer send-text 8671234001 /test  # Send '/test' text to the chat with chat_id '8671234001'
```

### Configuring Proxy (if needed)

`tg-signer` does not read system proxy settings, you can configure it using the `TG_PROXY` environment variable or the `--proxy` command option.

For example:

```
export TG_PROXY=socks5://127.0.0.1:7890
```

### Login

```
tg-signer login
```

Follow the prompts to enter your phone number and verification code to log in, and get the list of recent chats. Ensure that the chat you want to sign in to appears in the list.

### Running Check-in Tasks

```
tg-signer run
```

Follow the prompts to configure. The data and configuration are saved in the `.signer` directory. After running `tree .signer`, you will see:

```
.signer
├── latest_chats.json  # Recently fetched chats
├── me.json  # Personal information
└── signs
    └── openai  # Task name
        ├── config.json  # Check-in configuration
        └── sign_record.json  # Check-in records

3 directories, 4 files
```

### Sending a Message

```
tg-signer send-text 8671234001 hello  # Send 'hello' text to the chat with chat_id '8671234001'
```
