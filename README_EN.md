## Telegram Daily Auto Check-in / Personal, Group, Channel Message Monitoring & Auto Reply

[中文版](./README.md)

### Features

- Daily scheduled check-in with random time deviation
- Click keyboard buttons based on configured text
- Invoke AI for image recognition and keyboard clicking
- Monitor and auto-reply to personal, group, and channel messages
- Execute action flows based on configuration

  **...**

### Installation

Requires Python 3.10 or higher

```sh
pip install -U tg-signer
```

Or for performance optimization:

```sh
pip install "tg-signer[speedup]"
```

#### Docker

No pre-built image is provided. You can build your own image using the Dockerfile and [README](./docker/README.md) in the [docker](./docker) directory.

### Usage

```
Usage: tg-signer [OPTIONS] COMMAND [ARGS]...

  Use <subcommand> --help for usage instructions

Subcommand aliases:
  run_once -> run-once
  send_text -> send-text

Options:
  -l, --log-level [debug|info|warn|error]
                                  Log level: `debug`, `info`, `warn`, `error`
                                  [default: info]
  --log-file PATH                 Log file path (can be relative)  [default: tg-signer.log]
  -p, --proxy TEXT                Proxy address, e.g.: socks5://127.0.0.1:1080,
                                  overrides `TG_PROXY` env var  [env var: TG_PROXY]
  --session_dir PATH              Directory for TG Sessions (can be relative)  [default: .]
  -a, --account TEXT              Custom account name, session file will be <account>.session  [env
                                  var: TG_ACCOUNT; default: my_account]
  -w, --workdir PATH              tg-signer working directory for configs and check-in records  [default:
                                  .signer]
  --session-string TEXT           Telegram Session String,
                                  overrides `TG_SESSION_STRING` env var  [env var:
                                  TG_SESSION_STRING]
  --in-memory                     Store session in memory (default: False, stored in file)
  --help                          Show this message and exit.

Commands:
  export                  Export config (default: stdout)
  import                  Import config (default: stdin)
  list                    List existing configs
  list-members            List chat members (admin rights required for channels)
  list-schedule-messages  Show configured scheduled messages
  login                   Login account (to obtain session)
  logout                  Logout and delete session file
  monitor                 Configure and run monitoring
  multi-run               Run multiple accounts with one config
  reconfig                Reconfigure
  run                     Run check-in tasks based on config
  run-once                Run check-in task once (even if already executed today)
  schedule-messages       Batch configure Telegram's native scheduled messages
  send-text               Send one message (ensure session has "seen" the `chat_id`)
  version                 Show version
```

Examples:

```sh
tg-signer run
tg-signer run my_sign  # Run 'my_sign' task without confirmation
tg-signer run-once my_sign  # Run 'my_sign' task once
tg-signer send-text 8671234001 /test  # Send '/test' to chat_id '8671234001'
tg-signer send-text -- -10006758812 water  # For negative numbers, use POSIX style with '--' before '-'
tg-signer send-text --delete-after 1 8671234001 /test  # Send '/test' to '8671234001', delete after 1 second
tg-signer list-members --chat_id -1001680975844 --admin  # List channel admins
tg-signer schedule-messages --crontab '0 0 * * *' --next-times 10 -- -1001680975844 hello  # Send "hello" to '-1001680975844' at 00:00 daily for next 10 days
tg-signer monitor run  # Configure and run personal/group/channel message monitoring
tg-signer multi-run -a account_a -a account_b same_task  # Run 'account_a' and 'account_b' with 'same_task' config
```

### Proxy Configuration (if needed)

`tg-signer` doesn't read system proxy. Use `TG_PROXY` env var or `--proxy` parameter:

```sh
export TG_PROXY=socks5://127.0.0.1:7890
```

### Login

```sh
tg-signer login
```

Follow prompts to enter phone number and verification code. Recent chats will be listed - ensure your target chat is included.

### Send One Message

```sh
tg-signer send-text 8671234001 hello  # Send 'hello' to chat_id '8671234001'
```

### Run Check-in Task

```sh
tg-signer run
```

Or specify task name:

```sh
tg-signer run linuxdo
```

Follow configuration prompts.

#### Example:

```
Configuring task <linuxdo>
Check-in 1
1. Chat ID (from recent chats during login): 7661096533
2. Chat name (optional): jerry bot
3. Configure <Actions> in actual check-in order:
  1: Send plain text
  2: Send Dice emoji
  3: Click keyboard by text
  4: Select option by image
  5: Reply to math question

Action 1:
1. Select action by number: 1
2. Text to send: checkin
3. Continue adding actions? (y/N): y
Action 2:
4. Select action by number: 3
5. Keyboard button text: Check-in
6. Continue adding actions? (y/N): y
Action 3:
7. Select action by number: 4
Image recognition uses AI models (ensure model supports this)
8. Continue adding actions? (y/N): y
Action 4:
9. Select action by number: 5
Math questions use AI models.
10. Continue adding actions? (y/N): y
Action 5:
11. Select action by number: 2
12. Dice emoji to send (e.g. 🎲, 🎯): 🎲
13. Continue adding actions? (y/N): n
Ensure `OPENAI_API_KEY` and `OPENAI_BASE_URL` are set. Default model: "gpt-4o" (change via `OPENAI_MODEL`).
14. Delete check-in message after N seconds (0=immediate, empty=no delete), N: 10
╔════════════════════════════════════════════════╗
║ Chat ID: 7661096533                            ║
║ Name: jerry bot                                ║
║ Delete After: 10                               ║
╟────────────────────────────────────────────────╢
║ Actions Flow:                                  ║
║ 1. [Send plain text] Text: checkin             ║
║ 2. [Click keyboard by text] Click: 签到        ║
║ 3. [Select option by image]                    ║
║ 4. [Reply to math question]                    ║
║ 5. [Send Dice emoji] Dice: 🎲                  ║
╚════════════════════════════════════════════════╝
Check-in 1 configured successfully

Continue configuration? (y/N): n
Daily check-in time (time or crontab, e.g. '06:00:00' or '0 6 * * *'):
Random time deviation in seconds (default: 0): 300
```

### Configure and Run Monitoring

```sh
tg-signer monitor run my_monitor
```

Follow configuration prompts.

#### Example:

```
Configuring task <my_monitor>
Both chat_id and user_id support integer IDs or @-prefixed usernames (e.g. @neo)

Monitor item 1
1. Chat ID (from recent chats during login): -4573702599
2. Matching rule ('exact', 'contains', 'regex', 'all'): contains
3. Rule value (required): kfc
4. Only match messages from specific user IDs (comma-separated, empty for all): @neo
5. Default reply text: V Me 50
6. Regex to extract reply text from message:
7. Delete reply after N seconds (0=immediate, empty=no delete), N:
Continue? (y/N): y

Monitor item 2
1. Chat ID: -4573702599
2. Matching rule: regex
3. Rule value: 参与关键词：「.*?」 (Participation keyword: 「.*?」)
4. Only match from user IDs: 61244351
5. Default reply text:
6. Extraction regex: 参与关键词：「(?P<keyword>(.*?))」\n
7. Delete after N seconds: 5
Continue? (y/N): n
```

#### Explanation:

1. Both `chat_id` and `user_id` support integer IDs or @-prefixed usernames (may not exist). Example `chat_id` -4573702599 means rules only apply to that chat.

2. Matching rules (all case-insensitive):

   1. `exact`: Exact match (message must equal the value)

   2. `contains`: Contains match (e.g. "kfc" matches "I like KfC")

   3. `regex`: Regular expression (see [Python regex](https://docs.python.org/3/library/re.html)). Example "参与关键词：「.*?」" matches:
      "New lottery created... Participation keyword: 「我要抽奖」(I want to join) Please DM bot first"

   4. Can restrict to specific users (e.g. only group admins' lottery messages)

   5. Can set default reply text

   6. Can extract reply text using regex capture groups (e.g. "参与关键词：「(.*?)」\n" extracts "我要抽奖" from above example)

#### Example Output:

```
[INFO] [tg-signer] 2024-10-25 12:29:06,516 core.py 458 Starting monitoring...
[INFO] [tg-signer] 2024-10-25 12:29:37,034 core.py 439 Matched: MatchConfig(chat_id=-4573702599, rule=contains, rule_value=kfc), default_send_text=V me 50, send_text_search_regex=None
[INFO] [tg-signer] 2024-10-25 12:29:37,035 core.py 442 Sending: V me 50
[INFO] [tg-signer] 2024-10-25 12:30:02,726 core.py 439 Matched: MatchConfig(chat_id=-4573702599, rule=regex, rule_value=参与关键词：「.*?」), default_send_text=None, send_text_search_regex=参与关键词：「(?P<keyword>(.*?))」\n
[INFO] [tg-signer] 2024-10-25 12:30:02,727 core.py 442 Sending: 我要抽奖 (I want to join)
[INFO] [tg-signer] 2024-10-25 12:30:03,001 core.py 226 Message「我要抽奖」 to -4573702599 will be deleted after 5 seconds.
[INFO] [tg-signer] 2024-10-25 12:30:03,001 core.py 229 Waiting...
[INFO] [tg-signer] 2024-10-25 12:30:08,260 core.py 232 Message「我要抽奖」 to -4573702599 deleted!
```

### Changelog

#### 0.8.2
- Support for persistent OpenAI API and model configuration
- Minimum Python version requirement: 3.10
- Support for handling edited messages (e.g., keyboard)

#### 0.8.0
- Support for running multiple tasks simultaneously within a single account in the same process

#### 0.7.6
- fix: When monitoring multiple chats, messages are forwarded to each chat (#55)

#### 0.7.5
- Capture and log all RPC errors during task execution
- Bump kurigram version to 2.2.7

#### 0.7.4
- Support for fixed time intervals when executing multiple actions
- No longer limited to one execution per day when scheduling with `crontab`

#### 0.7.2

- Support forwarding messages to external endpoints via:
  - UDP
  - HTTP
- Replaced kurirogram with kurigram

#### 0.7.0

- Support sequential actions per chat:
  - Send text
  - Send dice
  - Click keyboard by text
  - Select option by image
  - Reply to math questions

#### 0.6.6
- Add Dice message support

#### 0.6.5
- Fix shared check-in records when running multiple accounts with same config

#### 0.6.4
- Add simple math question support
- Improve check-in config and message handling

#### 0.6.3

- Compatibility with kurigram 2.1.38 breaking change
> Remove coroutine param from run method [a7afa32](https://github.com/KurimuzonAkuma/pyrogram/commit/a7afa32df208333eecdf298b2696a2da507bde95)

#### 0.6.2

- Ignore chats where message sending fails during check-in

#### 0.6.1

- Support continuing image recognition after clicking buttons

#### 0.6.0

- Signer supports crontab scheduling
- Monitor adds `all` rule to match all messages
- Monitor supports ServerChan notifications
- Add `multi-run` for running multiple accounts with one config

#### 0.5.2

- Monitor supports AI-powered replies
- Add batch configuration for Telegram's native scheduled messages

#### 0.5.1

- Add `import`/`export` commands for config transfer

#### 0.5.0

- Click keyboard buttons by configured text
- Invoke AI for image-based keyboard clicking

### Data Storage

Configs and data are stored in `.signer` by default. Running `tree .signer` shows:

```
.signer
├── latest_chats.json  # Recent chats
├── me.json  # Personal info
├── monitors  # Monitoring
│   ├── my_monitor  # Task name
│       └── config.json  # Config
└── signs  # Check-ins
    └── linuxdo  # Task name
        ├── config.json  # Config
        └── sign_record.json  # Records

3 directories, 4 files
```
