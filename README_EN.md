## Telegram Daily Auto Sign-in / Personal, Group, and Channel Message Monitoring and Auto Reply

[中文版](./README.md)

### Installation

```sh
pip install -U tg-signer
```

Or to enhance the program's performance:

```sh
pip install "tg-signer[speedup]"
```

### Usage

```
Usage: tg-signer [OPTIONS] COMMAND [ARGS]...

  Use <subcommand> --help for usage instructions.

Subcommand aliases:
  run_once -> run-once
  send_text -> send-text

Options:
  -l, --log-level [debug|info|warn|error]
                                  Log level, `debug`, `info`, `warn`, `error`
                                  [default: info]
  --log-file PATH                 Path to log file, can be a relative path  [default: tg-signer.log]
  -p, --proxy TEXT                Proxy address, e.g., socks5://127.0.0.1:1080,
                                  will override the value of the environment variable `TG_PROXY`  [env var: TG_PROXY]
  --session_dir PATH              Directory to store TG Sessions, can be a relative path  [default: .]
  -a, --account TEXT              Custom account name, corresponding session file will be <account>.session  [env var: TG_ACCOUNT; default: my_account]
  -w, --workdir PATH              tg-signer working directory, used to store configurations and sign-in records, etc.  [default: .signer]
  --session-string TEXT           Telegram Session String,
                                  will override the value of the environment variable `TG_SESSION_STRING`  [env var: TG_SESSION_STRING]
  --in-memory                     Whether to store the session in memory, default is False (stored in file)
  --help                          Show this message and exit.

Commands:
  list          List existing configurations
  list-members  Query members of a chat (group or channel), admin permissions required for channels
  login         Log in to account (for obtaining session)
  logout        Log out of account and delete session file
  monitor       Configure and run monitoring
  reconfig      Reconfigure settings
  run           Run sign-in according to task configuration
  run-once      Run a sign-in task once, even if the task has already been executed today
  send-text     Send a message once, ensure the current session has "seen" the `chat_id`
  version       Show version
```

Example:

```sh
tg-signer run
tg-signer run my_sign  # Run the 'my_sign' task without prompts
tg-signer run-once my_sign  # Run the 'my_sign' task once immediately
tg-signer send-text 8671234001 /test  # Send '/test' text to chat_id '8671234001'
tg-signer send-text --delete-after 1 8671234001 /test  # Send '/test' to chat_id '8671234001', then delete the message after 1 second
tg-signer monitor run  # Configure personal, group, and channel message monitoring and auto-reply
```

### Configuring Proxy (if needed)

`tg-signer` does not use the system proxy automatically. You can configure the proxy using the `TG_PROXY` environment variable or the `--proxy` command option.

For example:

```sh
export TG_PROXY=socks5://127.0.0.1:7890
```

### Logging In

```sh
tg-signer login
```

Follow the prompts to enter your phone number and verification code to log in. This will retrieve a list of recent chats. Make sure the chat you want to sign in for is in the list.

### Sending a Single Message

```sh
tg-signer send-text 8671234001 hello  # Send 'hello' text to chat_id '8671234001'
```

### Running Sign-in Tasks

```sh
tg-signer run
```

Or execute a predefined task:

```sh
tg-signer run linuxdo
```

Follow the prompts for configuration.

#### Example:

```
Start configuring task <linuxdo>
First sign-in:
1. Chat ID (from the recent chats output during login): 10086
2. Sign-in text (e.g., /sign): /check_in
3. Wait N seconds before deleting the sign-in message (enter '0' to delete immediately, or press Enter to skip deletion), N: 5
Continue configuring sign-in? (y/N): n
4. Daily sign-in time (e.g., 06:00:00): 08:10:00
5. Random seconds for sign-in time deviation (default is 0): 10
```

### Configuring and Running Monitoring

```sh
tg-signer monitor run my_monitor
```

Follow the prompts for configuration.

#### Example:

```
Start configuring task <my_monitor>
Both integer IDs and string usernames are supported for chat and user IDs. Usernames must start with @, e.g., @neo

Configuring the 1st monitoring rule:
1. Chat ID (from the recent chats output during login): -4573702599
2. Matching rule ('exact', 'contains', 'regex'): contains
3. Rule value (cannot be empty): kfc
4. Match messages from specific user IDs only (separate multiple IDs with commas, press Enter to match all users): @neo
5. Default reply text: V Me 50
6. Regex to extract reply text:
7. Wait N seconds before deleting the message (enter '0' to delete immediately, or press Enter to skip deletion), N:
Continue configuring? (y/N): y

Configuring the 2nd monitoring rule:
1. Chat ID (from the recent chats output during login): -4573702599
2. Matching rule ('exact', 'contains', 'regex'): regex
3. Rule value (cannot be empty): Participation keyword: 「.*?」
4. Match messages from specific user IDs only (separate multiple IDs with commas, press Enter to match all users): 6181244351
5. Default reply text:
6. Regex to extract reply text: Participation keyword: 「(?P<keyword>(.*?))」\n
7. Wait N seconds before deleting the message (enter '0' to delete immediately, or press Enter to skip deletion), N: 5
Continue configuring? (y/N): n
```

#### Example Explanation:

1. Both `chat id` and `user id` support integer **IDs** and string **usernames**. Usernames must start with @, e.g., input "@neo" for "neo". Note that **usernames** may not always exist. In the example, `chat id` is -4573702599, indicating that the rule only applies to that specific chat.

2. Matching rules, all are **case-insensitive**:

   1. `exact`: exact match, the message must be exactly equal to the rule value

   2. `contains`: contains match, e.g., contains="kfc" would match a message like "I like MacDonalds rather than KfC" (case-insensitive)

   3. `regex`: regular expression, follow [Python regex](https://docs.python.org/3/library/re.html). If the message **contains** the regex, it matches. For example, "Participation keyword: 「.*?」" can match a message: "A new giveaway has been created...
      Participation keyword: 「I want to join」

      You are encouraged to DM the bot"

   4. Optionally, match messages from specific users, e.g., only from group admins instead of any random person.

   5. Optionally, set a default reply message to be sent automatically when a match is found.

   6. Regex can be used to extract specific parts of a message. For example, "Participation keyword: 「(.*?)」\n" can capture the keyword "I want to join" from the example message and send it automatically.



### Configuration and Data Storage Location

The data and configuration are stored by default in the `.signer` directory. Running `tree .signer` will display:

```
.signer
├── latest_chats.json  # Recent chats
├── me.json  # Personal info
└── signs
    └── linuxdo  # Sign-in task name
        ├── config.json  # Sign-in configuration
        └── sign_record.json  # Sign-in records

3 directories, 4 files
```
