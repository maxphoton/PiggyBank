# 🐷 PiggyBank Bot

> Real-time Telegram bot for monitoring PiggyBank assets and receiving instant notifications about epoch changes, new assets, and TVL changes.

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.24.0-green.svg)](https://docs.aiogram.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## ✨ Features

- 🔔 **Real-time Notifications** - Get instant alerts about asset changes
- 📊 **Asset Monitoring** - Track epoch changes, new assets, and TVL changes
- 🎯 **Selective Subscriptions** - Choose which assets to monitor with interactive checkboxes (✅/🔲)
- 📈 **Asset Statistics** - View current status of all assets with epoch via `/get_stats`
- 🛠️ **Admin Dashboard** - Export data, view statistics, and monitor logs
- 🧪 **Test Mode** - Test bot functionality with local data files
- 🐳 **Docker Support** - Easy deployment with Docker Compose
- 📝 **Comprehensive Logging** - Full logging with file and console output
- ⚡ **Async Architecture** - High-performance asynchronous operations

## 🚀 Quick Start

### Prerequisites

- Python 3.13+ or Docker
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

**Start the bot and configure subscriptions:**
```
/start
```

The bot will show you:
- A list of available assets with epoch
- Information about notification types you'll receive
- Interactive checkboxes to enable/disable notifications for each asset

Click on any asset to toggle notifications:
- ✅ = Notifications enabled
- 🔲 = Notifications disabled

**Notification types you'll receive:**
- 🔄 Epoch changes for subscribed assets
- 📈📉 Capacity changes (when TVL changes by more than 1)
- 🔧 Capacity limit changes (when lst_cap changes)

**View asset statistics:**
```
/get_stats
```

Shows all assets with epoch, including:
- Asset name and ticker
- Current epoch number
- Filling status (filled amount / capacity)
- Filling percentage

**View demo notifications:**
```
/demo
```

**View asset statistics:**
```
/get_stats
```

This command shows you all assets with epoch, their current status, filling percentage, and capacity information.

**View demo notifications:**
```
/demo
```

This command sends you all types of notifications so you can see what to expect.

**Notification Types:**
- 🆕 **New asset added** - Sent to all users when a new asset with epoch appears
  - Includes: Asset name, filling status (X / Y), link to platform
- 🔄 **New Epoch** - Sent to subscribed users when epoch number changes
  - Includes: Old → New epoch, filling status (X / Y), link to platform
- 📈/📉 **TVL changed** - Sent to subscribed users when TVL changes by more than 1
  - Includes: Change amount (with ± sign, precision to hundredths), filling status (X / Y), link to platform
  - 📈 for increase, 📉 for decrease
- 🔧 **Capacity limit changed** - Sent to subscribed users when lst_cap changes
  - Includes: Change amount (with ± sign, precision to hundredths), filling status (X / Y), link to platform

All notifications include direct links to the PiggyBank platform.

### For Administrators

**Get bot data and statistics:**
```
/get_data
```

This admin-only command exports:
- All database tables as CSV files (`users.csv`, `user_subscriptions.csv`)
- Bot usage statistics (users, subscriptions, top assets)
- Log file (`bot.log`)

**Admin receives:**
- ✅ Bot startup confirmation message
- Full access to data export and statistics

**Admin Notifications:**
- Bot startup confirmation (✅)
- Full access to bot data export via `/get_data`
- All `lst_tvl` changes are logged (but not sent as notifications)

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
1. Fetches current asset data from API (or test file in test mode)
2. Compares with saved data to detect changes
3. Generates notifications for:
   - **New assets with epoch** - Broadcast to all users when epoch key appears
   - **Epoch changes** - Sent to subscribed users when epoch number changes
   - **TVL changes** - Sent to subscribed users when `lst_tvl` changes by more than 1 (with ± sign, precision to hundredths)
   - **Capacity limit changes** - Sent to subscribed users when `lst_cap` changes (with ± sign, precision to hundredths)
4. Sends notifications to subscribed users in background
5. Updates saved data cache

**Important:**
- TVL notifications are only sent if the change is greater than 1 (absolute value)
- Capacity limit (`lst_cap`) notifications are sent for any change (not threshold-based)
- TVL appearance (when asset first gets `lst_tvl`) is not tracked separately (covered by epoch appearance)
- All notifications include filling status (filled X / capacity Y)

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

- All asset changes (epoch, lst_tvl, lst_cap) with details
- User actions (subscriptions, commands)
- Notification sending status
- API requests and responses
- Database operations
- Error details with full traceback

### Admin Monitoring

Administrators receive:
- ✅ Bot startup confirmation message
- Access to `/get_data` command for full export
- All `lst_tvl` changes are logged (but not sent as notifications)

## 🛠️ Technologies

- **Python 3.13+** - Programming language
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

- **Broadcast notifications** - New assets with epoch sent to all users
- **Targeted notifications** - Epoch changes, TVL changes, and capacity limit changes sent only to subscribed users
- **Threshold-based TVL alerts** - Only significant TVL changes (>1) trigger notifications
- **Capacity limit tracking** - All capacity limit (`lst_cap`) changes trigger notifications (no threshold)
- **Rich formatting** - HTML formatting with links, emojis (🆕, 🔄, 📈, 📉, 🔧), and capacity information
- **Precise change tracking** - Changes shown with ± sign and precision to hundredths (e.g., +123.45 or -67.89)

### Data Management

- **Automatic caching** - Asset data cached locally in JSON format
- **Change detection** - Compares current vs saved data with precision
- **CSV export** - Full database export for analysis (admin only)
- **Statistics** - Real-time bot usage statistics and asset statistics
- **Asset status view** - `/get_stats` command shows all assets with epoch, filling status, and percentages
- **Test mode** - Local testing without API calls using `test_api.json`

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
