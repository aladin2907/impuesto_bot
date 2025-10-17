# Telegram Parser Scripts

Scripts for parsing Telegram groups and building conversation threads.

## Setup

### 1. Get Telegram API Credentials

1. Go to https://my.telegram.org
2. Log in with your phone number
3. Go to "API development tools"
4. Create an application
5. Copy `api_id` and `api_hash`

### 2. Add to .env

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+34xxxxxxxxx
```

### 3. Install Dependencies

```bash
pip install telethon
```

## Test Parser

The test parser (`test_parser.py`) downloads messages from a group and saves them to JSON for inspection.

### Usage

```bash
# Basic usage (last 7 days)
python scripts/telegram/test_parser.py it_autonomos_spain

# Specify number of days
python scripts/telegram/test_parser.py it_autonomos_spain --days 14

# Custom output file
python scripts/telegram/test_parser.py chatfornomads --output nomads_messages.json

# Limit number of messages
python scripts/telegram/test_parser.py it_autonomos_spain --limit 500 --days 7
```

### Examples

```bash
# IT Autonomos - last week
python scripts/telegram/test_parser.py it_autonomos_spain

# Digital Nomads - last 2 weeks
python scripts/telegram/test_parser.py chatfornomads --days 14
```

### First Time Setup

When you run the script for the first time, Telegram will send you a verification code. Enter it when prompted.

The session will be saved to `telegram_session.session` file, so you won't need to verify again.

### Output Format

Messages are saved as JSON array:

```json
[
  {
    "id": 12345,
    "date": "2024-01-15T14:30:00+00:00",
    "text": "Message text here...",
    "sender_id": 123456789,
    "reply_to": null,
    "views": 150,
    "forwards": 5
  },
  ...
]
```

## Full History Download with Threads

Download ENTIRE chat history and organize into conversation threads.

### What are threads?

A thread is a conversation chain:
- Root message (original post or question)
- All replies to that message
- All replies to replies (nested, any depth)
- Single messages with no replies are also threads

**Thread metadata:**
- `thread_id`: ID of root message
- `first_message_date`: When thread started
- `last_updated`: Date of most recent message in thread
- `message_count`: Total messages in thread
- `max_depth`: Maximum nesting level

### Usage

#### 1. Download Full History

```bash
# Download ALL messages from IT Autonomos and build threads
python scripts/telegram/download_full_history.py it_autonomos_spain --output it_threads.json

# Digital Nomads group
python scripts/telegram/download_full_history.py chatfornomads --output nomads_threads.json
```

This will:
- Download entire chat history (may take 5-10 minutes)
- Build conversation threads
- Save to JSON with thread structure

#### 2. Weekly Updates (Incremental)

```bash
# Update existing threads with new messages from last 7 days
python scripts/telegram/update_threads_weekly.py it_autonomos_spain --file it_threads.json

# Custom period (e.g., last 14 days)
python scripts/telegram/update_threads_weekly.py it_autonomos_spain --file it_threads.json --days 14
```

This will:
- Load existing threads
- Fetch new messages since last update
- Merge new messages into existing threads
- Update thread metadata (last_updated)
- Create backup before saving

### Output Format

```json
{
  "group": "it_autonomos_spain",
  "group_title": "IT Autonomos [Spain]",
  "downloaded_at": "2025-10-01T12:00:00",
  "last_updated": "2025-10-01T12:00:00",
  "total_messages": 5234,
  "total_threads": 1847,
  "threads": [
    {
      "thread_id": 12345,
      "first_message_date": "2025-01-15T10:30:00",
      "last_updated": "2025-01-15T14:20:00",
      "message_count": 5,
      "max_depth": 2,
      "messages": [
        {
          "id": 12345,
          "date": "2025-01-15T10:30:00",
          "text": "Как открыть автономо?",
          "sender_id": 123456,
          "depth": 0
        },
        {
          "id": 12346,
          "date": "2025-01-15T11:00:00",
          "text": "Нужно обратиться в Hacienda...",
          "sender_id": 789012,
          "depth": 1
        }
      ]
    }
  ]
}
```

### Automation (Weekly)

Add to crontab for automatic weekly updates:

```bash
# Every Monday at 2 AM
0 2 * * 1 cd /path/to/project && /path/to/venv/bin/python scripts/telegram/update_threads_weekly.py it_autonomos_spain --file data/it_threads.json
```

### Benefits of Thread Structure

1. **Context preserved** - Questions with their answers
2. **Quality scoring** - Longer threads = more discussion = valuable
3. **Better RAG** - Bot can cite entire discussion, not just fragments
4. **Deduplication** - Related messages grouped together
5. **Time tracking** - See when discussions are active

---

*Developed by NAIL - Nahornyi AI Lab*
