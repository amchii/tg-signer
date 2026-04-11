## Telegram Daily Auto Check-in / Personal, Group, and Channel Message Monitoring with Auto Reply

[简体中文](./README.md)

### Features

- Daily scheduled check-ins with random time deviation
- Click keyboard buttons based on configured text
- Use AI for image recognition and click the matching keyboard button
- Monitor personal, group, and channel messages, then forward or auto-reply
- Execute action flows based on configuration

  **...**

### Installation

Requires Python 3.10 or above.

```sh
pip install -U tg-signer
```

Or install the performance extras:

```sh
pip install "tg-signer[speedup]"
```

#### WebUI

`tg-signer` also ships with a WebUI. Install it with:

```sh
pip install "tg-signer[gui]"
```

![webgui](./assets/webui.jpeg)

### Docker

#### GitHub Container Registry

Two prebuilt images are published on GitHub Container Registry:
`ghcr.io/amchii/tg-signer:<tag>` (CLI) and
`ghcr.io/amchii/tg-signer:<tag>-webui` (CLI + WebUI).

#### Local

If you want to build the image yourself, the local build flow is still available.
See the Dockerfiles in the [docker](./docker) directory and its
[README](./docker/README.md).

### Usage

```text
Usage: tg-signer [OPTIONS] COMMAND [ARGS]...

  Use <subcommand> --help for usage instructions

Subcommand aliases:
  run_once -> run-once
  send_text -> send-text

Options:
  -l, --log-level [debug|info|warn|error]
                                  Log level: `debug`, `info`, `warn`, `error`
                                  [default: info]
  --log-file PATH                 Log file path, can be relative  [default: logs/tg-
                                  signer.log]
  --log-dir PATH                  Log directory, can be relative  [default: logs]
  -p, --proxy TEXT                Proxy address, for example:
                                  socks5://127.0.0.1:1080. Overrides the
                                  `TG_PROXY` environment variable  [env var:
                                  TG_PROXY]
  --session_dir PATH              Directory used to store TG sessions, can be
                                  relative  [default: .]
  -a, --account TEXT              Custom account name. The session file will be
                                  named <account>.session  [env var: TG_ACCOUNT;
                                  default: my_account]
  -w, --workdir PATH              tg-signer working directory, used to store
                                  configs and check-in records  [default: .signer]
  --session-string TEXT           Telegram Session String. Overrides the
                                  `TG_SESSION_STRING` environment variable
                                  [env var: TG_SESSION_STRING]
  --in-memory                     Store the session in memory instead of a file
  --help                          Show this message and exit.

Commands:
  export                  Export configuration, defaults to stdout
  import                  Import configuration, defaults to stdin
  list                    List existing configurations
  list-members            List chat members (groups or channels; channels require
                          admin permissions)
  list-sign-records       List the latest N check-in records
  list-topics             List group topic IDs (`message_thread_id`)
  list-schedule-messages  Show configured scheduled messages
  llm-config              Configure the LLM API
  login                   Log in to an account (used to obtain a session)
  migrate-sign-records    Migrate check-in records from JSON to SQLite (keeps the
                          original files by default)
  logout                  Log out and delete the session file
  monitor                 Configure and run monitoring
  multi-run               Run multiple accounts with a shared configuration
  reconfig                Reconfigure
  run                     Run check-in tasks based on task configuration
  run-once                Run a check-in task once, even if it has already run
                          today
  schedule-messages       Batch configure Telegram's built-in scheduled messages
  send-dice               Send one DICE message. Make sure the current session has
                          already "seen" this `chat_id`
  send-text               Send one text message. Make sure the current session has
                          already "seen" this `chat_id`
  version                 Show version
  webgui                  Start the WebGUI (requires
                          `pip install "tg-signer[gui]"`)
```

Examples:

```sh
tg-signer run
tg-signer run my_sign  # Run the 'my_sign' task directly, without prompting
tg-signer run-once my_sign  # Run the 'my_sign' task once directly
tg-signer list-sign-records linuxdo -n 5  # View the latest 5 check-in records for task linuxdo
tg-signer migrate-sign-records  # Migrate check-in records under .signer/signs to SQLite
tg-signer send-text 8671234001 /test  # Send '/test' to chat_id '8671234001'
tg-signer send-text @neo /test  # Send '/test' to username '@neo'
tg-signer send-text --message-thread-id 1 -- -1003763902761 checkin  # Send to a group topic (message_thread_id=1)
tg-signer send-text -- -10006758812 water  # For negative numbers, use POSIX style and add '--' before '-'
tg-signer send-text --delete-after 1 8671234001 /test  # Send '/test' to chat_id '8671234001' and delete it after 1 second
tg-signer list-members --chat_id -1001680975844 --admin  # List channel admins
tg-signer list-topics --chat_id -1003763902761 --limit 50  # List group topics and message_thread_id
tg-signer schedule-messages --crontab '0 0 * * *' --next-times 10 -- -1001680975844 hello  # Send a message to '-1001680975844' at 00:00 for the next 10 days
tg-signer schedule-messages --crontab '0 0 * * *' --next-times 3 --message-thread-id 1 -- -1003763902761 hello  # Configure scheduled messages for a group topic
tg-signer monitor run  # Configure and run personal/group/channel message monitoring and auto reply
tg-signer multi-run -a account_a -a account_b same_task  # Run 'account_a' and 'account_b' using the same 'same_task' config
tg-signer webgui --auth-code averycomplexcode  # Start the WebGUI
```

### Configure a Proxy (Optional)

`tg-signer` does not read the system proxy. Use the `TG_PROXY` environment
variable or the `--proxy` argument instead.

For example:

```sh
export TG_PROXY=socks5://127.0.0.1:7890
```

### Login

```sh
tg-signer login
```

Follow the prompts to enter your phone number and verification code. The command
will print your recent chats, so make sure the chat you want to use for
check-ins is included.

Signer `chat_id` also supports integer IDs and `@`-prefixed usernames such as
`@neo`.

For forum-style groups, the login output also prints each topic's
`message_thread_id`, which can be used directly with `--message-thread-id`.

### Get Group Topic IDs

```sh
tg-signer list-topics --chat_id -1003763902761
```

This prints the visible topics in the forum group, including each
`message_thread_id`, title, and status, which makes topic-based configuration
much easier.

### Send a Message Once

```sh
tg-signer send-text 8671234001 hello  # Send 'hello' to chat_id '8671234001'
tg-signer send-text @neo hello  # Send 'hello' to username '@neo'
```

### Run a Check-in Task

```sh
tg-signer run
```

Or specify the task name in advance:

```sh
tg-signer run linuxdo
```

Then follow the prompts to configure it.

#### Example

```text
Start configuring task <linuxdo>
Check-in 1
1. Chat ID (from recent chats during login or @username): 7661096533
2. Chat name (optional): jerry bot
3. Send to a topic (`message_thread_id`)? (y/N): y
4. message_thread_id: 1
5. Start configuring <actions>. Please configure them in the real check-in order.
  1: Send plain text
  2: Send a Dice emoji
  3: Click a keyboard button based on text
  4: Select an option based on an image
  5: Reply to a math question

Action 1:
1. Enter the number of the action: 1
2. Enter the text to send: checkin
3. Continue adding actions? (y/N): y
Action 2:
1. Enter the number of the action: 3
2. Enter the keyboard button text to click: Check in
3. Continue adding actions? (y/N): y
Action 3:
1. Enter the number of the action: 4
Image recognition uses the configured LLM. Make sure your model supports image input.
2. Continue adding actions? (y/N): y
Action 4:
1. Enter the number of the action: 5
Math questions are answered by the configured LLM.
2. Continue adding actions? (y/N): y
Action 5:
1. Enter the number of the action: 2
2. Enter the dice emoji to send (for example 🎲, 🎯): 🎲
3. Continue adding actions? (y/N): n
Before running, set `OPENAI_API_KEY` and `OPENAI_BASE_URL` correctly via environment variables.
The default model is "gpt-4o", and can be changed with `OPENAI_MODEL`.
6. Delete the check-in message after N seconds (wait N seconds after sending before deleting; enter '0' for immediate deletion, or press Enter to keep it), N: 10
╔════════════════════════════════════════════════╗
║ Chat ID: 7661096533                            ║
║ Name: jerry bot                                ║
║ Message Thread ID: 1                           ║
║ Delete After: 10                               ║
╟────────────────────────────────────────────────╢
║ Actions Flow:                                  ║
║ 1. [Send plain text] Text: checkin             ║
║ 2. [Click by text] Click: Check in             ║
║ 3. [Select by image]                           ║
║ 4. [Reply to math question]                    ║
║ 5. [Send Dice emoji] Dice: 🎲                  ║
╚════════════════════════════════════════════════╝
Check-in 1 configured successfully

Continue configuring check-ins? (y/N): n
Daily check-in time (time or crontab expression, such as '06:00:00' or '0 6 * * *'):
Random time deviation in seconds (default is 0): 300
```

### Configure and Run Monitoring

```sh
tg-signer monitor run my_monitor
```

Then follow the prompts.

#### Example

```text
Start configuring task <my_monitor>
Both chat IDs and user IDs support either integer IDs or string usernames. Usernames must start with @, such as @neo.

Configure monitor item 1
1. Chat ID (the ID shown in the recent chats output during login): -4573702599
2. Match rule ('exact', 'contains', 'regex', 'all'): contains
3. Rule value (required): kfc
4. Only match messages from specific user IDs (comma-separated; press Enter to match all): @neo
5. Default text to send: V Me 50
6. Regex used to extract the text to send from the message:
7. Delete the sent message after N seconds (wait N seconds after sending before deleting; enter '0' for immediate deletion, or press Enter to keep it), N:
Continue configuring? (y/N): y

Configure monitor item 2
1. Chat ID (the ID shown in the recent chats output during login): -4573702599
2. Match rule ('exact', 'contains', 'regex'): regex
3. Rule value (required): Participation keyword: 「.*?」
4. Only match messages from specific user IDs (comma-separated; press Enter to match all): 61244351
5. Default text to send:
6. Regex used to extract the text to send from the message: Participation keyword: 「(?P<keyword>(.*?))」\n
7. Delete the sent message after N seconds (wait N seconds after sending before deleting; enter '0' for immediate deletion, or press Enter to keep it), N: 5
Continue configuring? (y/N): y

Configure monitor item 3
1. Chat ID (the ID shown in the recent chats output during login): -4573702599
2. Match rule (exact, contains, regex, all): all
3. Only match messages from specific user IDs (comma-separated; press Enter to match all):
4. Always ignore messages sent by yourself (y/N): y
5. Default text to send (press Enter if not needed):
6. Use AI to reply? (y/N): n
7. Regex used to extract the text to send from the message (press Enter if not needed):
8. Push messages through ServerChan? (y/N): n
9. Forward to external endpoints (UDP, HTTP)? (y/N): y
10. Forward to UDP? (y/N): y
11. Enter the UDP server address and port (for example `127.0.0.1:1234`): 127.0.0.1:9999
12. Forward to HTTP? (y/N): y
13. Enter the HTTP endpoint (for example `http://127.0.0.1:1234`): http://127.0.0.1:8000/tg/user1/messages
Continue configuring? (y/N): n
```

#### Explanation

1. Both `chat_id` and `user_id` support integer IDs and string usernames.
   Usernames must start with `@`, so use `@neo` instead of `neo`. Note that a
   username may not exist. In the example above, `chat_id=-4573702599` means the
   rule only applies to that chat.

2. Matching rules are currently all case-insensitive:

   1. `exact` means exact match. The message content must equal the configured
      value.

   2. `contains` means substring matching. For example, if `contains="kfc"`,
      the message `"I like MacDonalds rather than KfC"` still matches.

   3. `regex` means regular expression matching. See
      [Python regular expressions](https://docs.python.org/3/library/re.html).
      A match is triggered as soon as the pattern is found anywhere in the
      message. In the example above, `Participation keyword: 「.*?」` can match
      a message like:

      `A new lottery has been created... Participation keyword: 「I want to join」`

      `Please DM the bot first`

   4. You can restrict matches to messages from specific users only, for
      example, group admins instead of any random participant.

   5. You can configure a default outgoing text, meaning the configured text is
      sent immediately whenever a message matches.

   6. You can extract outgoing text with a regex such as
      `Participation keyword: 「(.*?)」\n`. Use parentheses `(...)` to capture the
      text you want. That pattern can extract `I want to join` from the example
      in step 3 and send it automatically.

3. The `Message` structure looks like this:

```json
{
    "_": "Message",
    "id": 2950,
    "from_user": {
        "_": "User",
        "id": 123456789,
        "is_self": false,
        "is_contact": false,
        "is_mutual_contact": false,
        "is_deleted": false,
        "is_bot": false,
        "is_verified": false,
        "is_restricted": false,
        "is_scam": false,
        "is_fake": false,
        "is_support": false,
        "is_premium": false,
        "is_contact_require_premium": false,
        "is_close_friend": false,
        "is_stories_hidden": false,
        "is_stories_unavailable": true,
        "is_business_bot": false,
        "first_name": "linux",
        "status": "UserStatus.ONLINE",
        "next_offline_date": "2025-05-30 11:52:40",
        "username": "linuxdo",
        "dc_id": 5,
        "phone_number": "*********",
        "photo": {
            "_": "ChatPhoto",
            "small_file_id": "AQADBQADqqcxG6hqrTMAEAIAA6hqrTMABLkwVDcqzBjAAAQeBA",
            "small_photo_unique_id": "AgADqqcxG6hqrTM",
            "big_file_id": "AQADBQADqqcxG6hqrTMAEAMAA6hqrTMABLkwVDcqzBjAAAQeBA",
            "big_photo_unique_id": "AgADqqcxG6hqrTM",
            "has_animation": false,
            "is_personal": false
        },
        "added_to_attachment_menu": false,
        "inline_need_location": false,
        "can_be_edited": false,
        "can_be_added_to_attachment_menu": false,
        "can_join_groups": false,
        "can_read_all_group_messages": false,
        "has_main_web_app": false
    },
    "date": "2025-05-30 11:47:46",
    "chat": {
        "_": "Chat",
        "id": -52737131599,
        "type": "ChatType.GROUP",
        "is_creator": true,
        "is_deactivated": false,
        "is_call_active": false,
        "is_call_not_empty": false,
        "title": "Test Group",
        "has_protected_content": false,
        "members_count": 4,
        "permissions": {
            "_": "ChatPermissions",
            "can_send_messages": true,
            "can_send_media_messages": true,
            "can_send_other_messages": true,
            "can_send_polls": true,
            "can_add_web_page_previews": true,
            "can_change_info": true,
            "can_invite_users": true,
            "can_pin_messages": true,
            "can_manage_topics": true
        }
    },
    "from_offline": false,
    "show_caption_above_media": false,
    "mentioned": false,
    "scheduled": false,
    "from_scheduled": false,
    "edit_hidden": false,
    "has_protected_content": false,
    "text": "test, hello",
    "video_processing_pending": false,
    "outgoing": false
}
```

#### Example Runtime Output

```text
[INFO] [tg-signer] 2024-10-25 12:29:06,516 core.py 458 Starting monitoring...
[INFO] [tg-signer] 2024-10-25 12:29:37,034 core.py 439 Matched monitor item: MatchConfig(chat_id=-4573702599, rule=contains, rule_value=kfc), default_send_text=V me 50, send_text_search_regex=None
[INFO] [tg-signer] 2024-10-25 12:29:37,035 core.py 442 Sending text: V me 50
[INFO] [tg-signer] 2024-10-25 12:30:02,726 core.py 439 Matched monitor item: MatchConfig(chat_id=-4573702599, rule=regex, rule_value=参与关键词：「.*?」), default_send_text=None, send_text_search_regex=参与关键词：「(?P<keyword>(.*?))」\n
[INFO] [tg-signer] 2024-10-25 12:30:02,727 core.py 442 Sending text: 我要抽奖
[INFO] [tg-signer] 2024-10-25 12:30:03,001 core.py 226 Message "我要抽奖" to -4573702599 will be deleted after 5 seconds.
[INFO] [tg-signer] 2024-10-25 12:30:03,001 core.py 229 Waiting...
[INFO] [tg-signer] 2024-10-25 12:30:08,260 core.py 232 Message "我要抽奖" to -4573702599 deleted!
```

### Changelog

#### 0.8.6
- Support Telegram forum group topics via `message_thread_id`
- Discover group topics during login, and add `list-topics` for querying topic IDs
- `send-text`, `send-dice`, `schedule-messages`, check-in configuration, and WebUI now support sending to a specific topic
- Migrate check-in records to SQLite, and add `list-sign-records` plus `migrate-sign-records`
- Keep compatibility for reading the old `sign_record.json`, and auto-import legacy records when running tasks
- Publish official GHCR images: `ghcr.io/amchii/tg-signer:<tag>` and `ghcr.io/amchii/tg-signer:<tag>-webui`
- Improve compatibility for topic discovery and message delivery in forum groups, channel DMs, and similar scenarios

#### 0.8.5
- `kurigram>=2.2.19,<2.3.0`
- Add concurrent request throttling when multiple tasks run under a single account

#### 0.8.4
- Add WebGUI
- Add the `--log-dir` option, change the default log directory to `logs`, and split warning and error logs into separate files

#### 0.8.2
- Support persistent OpenAI API and model configuration
- Minimum supported Python version is now 3.10
- Support handling edited messages (for example, updated keyboards)

#### 0.8.0
- Support running multiple tasks in the same process for a single account

#### 0.7.6
- Fix: when monitoring multiple chats, forwarded messages are delivered to each target chat correctly (#55)

#### 0.7.5
- Capture and log all RPC errors during task execution
- Bump kurigram to version 2.2.7

#### 0.7.4
- Support fixed intervals when executing multiple actions
- Remove the once-per-day limitation when scheduling with `crontab`

#### 0.7.2
- Support forwarding messages to external endpoints through:
  - UDP
  - HTTP
- Replace kurirogram with kurigram

#### 0.7.0
- Support executing multiple actions sequentially for each chat session. Supported action types:
  - Send text
  - Send dice
  - Click a keyboard button by text
  - Select an option by image
  - Reply to a math question

#### 0.6.6
- Add support for sending DICE messages

#### 0.6.5
- Fix shared check-in records when multiple accounts run with the same configuration

#### 0.6.4
- Add support for simple math questions
- Improve check-in configuration and message handling

#### 0.6.3
- Compatible with the breaking change introduced in kurigram 2.1.38
> Remove coroutine param from run method [a7afa32](https://github.com/KurimuzonAkuma/pyrogram/commit/a7afa32df208333eecdf298b2696a2da507bde95)

#### 0.6.2
- Ignore chats where sending a check-in message fails

#### 0.6.1
- Support continuing with image recognition after clicking a button by text

#### 0.6.0
- Add crontab scheduling to Signer
- Add the `all` rule to Monitor for matching all messages
- Add ServerChan push support for Monitor
- Add `multi-run` so multiple accounts can run with one shared configuration

#### 0.5.2
- Monitor supports AI-based replies
- Add batch configuration for Telegram's built-in scheduled messages

#### 0.5.1
- Add `import` and `export` commands for configuration import/export

#### 0.5.0
- Click keyboard buttons based on configured text
- Use AI to recognize images and click keyboard buttons

### Configuration and Data Storage

Data and configuration are stored in the `.signer` directory by default. If you
run `tree .signer`, you will see:

```text
.signer
├── .openai_config.json  # Optional LLM configuration
├── data.sqlite3  # SQLite check-in record database
├── monitors  # Monitor tasks
│   ├── my_monitor  # Monitor task name
│       └── config.json  # Monitor configuration
├── users
│   └── 123456789
│       ├── latest_chats.json  # Recently fetched chats
│       └── me.json  # Personal profile
└── signs  # Check-in tasks
    └── linuxdo  # Check-in task name
        ├── config.json  # Check-in configuration
        ├── 123456789
        │   └── sign_record.json  # Legacy JSON check-in records (still supported for migration)
        └── sign_record.json  # Even older JSON path (still supported for migration)

5 directories, 6 files
```

After migrating to SQLite, new check-in records are written only to
`data.sqlite3`, but old `sign_record.json` files can still be read. If legacy
JSON is detected while running a task, the program prints a notice and tries to
import that task's historical records into SQLite automatically.
