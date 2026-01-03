# 🐷 PiggyBank Bot

> Real-time Telegram bot for monitoring PiggyBank assets and receiving instant notifications about epoch changes, new assets, and available space.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.24.0-green.svg)](https://docs.aiogram.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## ✨ Features

- 🔔 **Real-time Notifications** - Get instant alerts about asset changes
- 📊 **Asset Monitoring** - Track epoch changes, new assets, and available space
- 🎯 **Selective Subscriptions** - Choose which assets to monitor with interactive checkboxes
- 📈 **Admin Dashboard** - Export data, view statistics, and monitor logs
- 🧪 **Test Mode** - Test bot functionality with local data files
- 🐳 **Docker Support** - Easy deployment with Docker Compose
- 📝 **Comprehensive Logging** - Full logging with file and console output
- ⚡ **Async Architecture** - High-performance asynchronous operations

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ or Docker
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- Telegram User ID ([@userinfobot](https://t.me/userinfobot))

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd piggybank_bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
# Copy example file
cp env.example .env
# Edit .env and add your actual values
nano .env  # or use your preferred editor
```

Required variables:
- `BOT_TOKEN` - Your Telegram bot token
- `ADMIN_ID` - Your Telegram user ID

4. **Run the bot**
```bash
python bot.py
```

## 🐳 Docker Deployment

### Using Docker Compose

1. **Create `.env` file**
```env
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_user_id
DATA_DIR=data
```

2. **Create data directory**
```bash
mkdir -p data
```

3. **Start the bot**
```bash
docker-compose up -d
```

4. **View logs**
```bash
docker-compose logs -f
# or
tail -f data/bot.log
```

All data (database, logs, cache) will be persisted in the `data/` directory.

## 📖 Usage

### For Users

**Start the bot:**
```
/start
```

The bot will show you a list of available assets with epoch. Click on any asset to enable/disable notifications:
- ✅ = Notifications enabled
- ☐ = Notifications disabled

**View demo notifications:**
```
/demo
```

This command sends you all types of notifications so you can see what to expect.

**Notification Types:**
- 🆕 **New asset added** - Sent to all users when a new asset with epoch appears
- 🔄 **New Epoch** - Sent to subscribed users when epoch number changes
- ✅ **Space available** - Sent to subscribed users when space becomes available (when `lst_tvl < lst_cap`)

Each notification includes:
- Asset name and ticker
- Free space information (if available)
- Direct link to PiggyBank platform

### For Administrators

**Get bot data and statistics:**
```
/get_data
```

This command exports:
- All database tables as CSV files (`users.csv`, `user_subscriptions.csv`)
- Bot statistics (users, subscriptions, top assets)
- Log file (`bot.log`)

**Admin Notifications:**
- All `lst_tvl` changes are logged and sent to admin
- Bot startup confirmation
- Full access to bot data export

## 🏗️ Architecture

### Core Components

- **`bot.py`** - Main bot logic, handlers, and background tasks
- **`database.py`** - SQLite database operations and data export
- **`config.py`** - Configuration management and environment variables

### Database Schema

**`users` table:**
- `user_id` (PRIMARY KEY) - Telegram User ID
- `username` - Telegram username
- `first_name`, `last_name` - User names
- `created_at` - Registration timestamp

**`user_subscriptions` table:**
- `id` (PRIMARY KEY) - Subscription ID
- `user_id` (FOREIGN KEY) - User ID
- `asset_ticker` - Asset ticker symbol
- `asset_name` - Asset display name
- `created_at` - Subscription timestamp
- UNIQUE(user_id, asset_ticker)

### Background Monitoring

The bot runs a background task every minute that:
1. Fetches current asset data
2. Compares with saved data to detect changes
3. Generates notifications for:
   - New assets with epoch (broadcast to all users)
   - Epoch changes (sent to subscribed users)
   - Available space (sent to subscribed users)
   - `lst_tvl` changes (admin only, with decimal precision)
4. Sends notifications to subscribed users
5. Updates saved data cache

## 📁 Project Structure

```
piggybank_bot/
├── bot.py                 # Main bot application
├── database.py            # Database operations
├── config.py              # Configuration
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
├── env.example            # Environment variables example
├── README.md              # This file
│
├── data/                  # Data directory (created automatically)
│   ├── users.db          # SQLite database
│   ├── bot.log           # Application logs
│   ├── assets_data.json  # Asset data cache
│   └── test_api.json     # Test data file (for TEST_API mode)
│
└── .env                   # Environment variables (not in git)
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BOT_TOKEN` | Telegram bot token from [@BotFather](https://t.me/BotFather) | Yes | - |
| `ADMIN_ID` | Your Telegram User ID | Yes | - |
| `API_URL` | API endpoint URL | No | (see config.py) |
| `TEST_API` | Test mode: load data from file instead of API | No | `false` |
| `DATA_DIR` | Data directory path (empty = root) | No | empty |
| `DATA_FILE` | Assets cache file path (only if DATA_DIR empty) | No | `assets_data.json` |
| `DB_FILE` | Database file path (only if DATA_DIR empty) | No | `users.db` |
| `LOG_FILE` | Log file path (only if DATA_DIR empty) | No | `bot.log` |
| `TEST_API_FILE` | Test data file path (only if DATA_DIR empty) | No | `test_api.json` |

### Test Mode

Enable test mode by setting `TEST_API=true` in `.env`. In test mode:
- Data is loaded from `test_api.json` instead of making API calls
- Perfect for testing changes without affecting real data
- Edit `test_api.json` to simulate different scenarios

## 📊 Monitoring & Logging

### Logging Levels

- **INFO** - Important events (startup, changes, notifications)
- **DEBUG** - Detailed information
- **WARNING** - Warnings and non-critical errors
- **ERROR** - Errors with full traceback

### Log Files

Logs are written to:
- **File**: `data/bot.log` (or `bot.log` in root)
- **Console**: Standard output
- **Mode**: Append (logs persist across restarts)

### What Gets Logged

- All asset changes (epoch, lst_tvl)
- User actions (subscriptions, commands)
- Notification sending status
- API requests and responses
- Database operations
- Error details with full traceback

### Admin Monitoring

Administrators receive:
- Notifications about all `lst_tvl` changes (with decimal precision)
- Bot startup confirmation
- Access to `/get_data` command for full export

## 🛠️ Technologies

- **Python 3.11+** - Programming language
- **aiogram 3.24.0** - Telegram Bot API framework
- **aiohttp 3.13.2** - Async HTTP client
- **aiosqlite 0.22.1** - Async SQLite driver
- **python-dotenv 1.0.1** - Environment variable management

## 🔒 Security

- ✅ Bot token stored in environment variables
- ✅ `.env` file excluded from version control
- ✅ Admin-only commands with ID verification
- ✅ Input validation and error handling
- ✅ Safe type conversions
- ✅ SQL injection protection via parameterized queries

## 📈 Features in Detail

### Smart Notifications

- **Broadcast notifications** - New assets sent to all users
- **Targeted notifications** - Epoch changes and space availability sent only to subscribed users
- **Admin alerts** - All `lst_tvl` changes reported to administrator with decimal precision
- **Rich formatting** - HTML formatting with links and emojis

### Data Management

- **Automatic caching** - Asset data cached locally
- **Change detection** - Compares current vs saved data with precision
- **CSV export** - Full database export for analysis
- **Statistics** - Real-time bot usage statistics
- **Test mode** - Local testing without API calls

### Performance

- **Async operations** - Non-blocking I/O operations
- **Background tasks** - Monitoring runs independently
- **Efficient queries** - Optimized database operations
- **Error resilience** - Graceful error handling
- **Rate limiting** - Delays between notification sends

## 🐛 Troubleshooting

### Common Issues

**Bot doesn't start:**
- Check `BOT_TOKEN` in `.env` (required)
- Verify `ADMIN_ID` is correct (required)
- Check logs in `data/bot.log`
- Ensure all dependencies are installed

**No notifications:**
- Ensure bot is running
- Check user subscriptions with `/start`
- Verify data source is accessible (API or test file)
- Check background task logs

**Docker issues:**
- Ensure `data/` directory exists and is writable
- Check `docker-compose logs` for errors
- Verify environment variables are set in `.env`
- Check file permissions

**Test mode not working:**
- Ensure `TEST_API=true` in `.env`
- Verify `test_api.json` file exists
- Check file path matches `TEST_API_FILE` setting

## 📝 License

This project is provided as-is for monitoring PiggyBank assets.

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows existing style
- All features are tested
- Documentation is updated
- Test mode works correctly

## 📞 Support

For issues and questions:
1. Check logs in `data/bot.log`
2. Review configuration in `.env`
3. Use `/demo` command to test notifications
4. Check Docker logs if using containers
5. Verify test mode if testing locally

---

**Made with ❤️ for PiggyBank community**
