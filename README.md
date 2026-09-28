# 🎮 Steam Deal Bot

Telegram bot for finding and tracking Steam game deals.

The bot helps users discover discounted games, save favorites, configure deal preferences, and receive notifications about new offers.

## ✨ Features

* 🔎 Search and browse Steam game deals
* 💰 Filter deals by discount
* ❤️ Add games to favorites
* 📋 View saved favorites
* ⚙️ Personal deal settings
* 🔔 Scheduled deal notifications
* 👥 Support for group chats
* 💳 Telegram Stars donations
* 🌐 External API integration

## 🛠 Tech Stack

* **Python**
* **Aiogram 3**
* **asyncio**
* **SQLite**
* **aiosqlite**
* **APScheduler**
* **REST API**
* **aiohttp**
* **python-dotenv**
* **Telegram Bot API**

## 📁 Project Structure

```text
steam_deal_bot/
├── handlers/
├── services/
├── database/
├── utils/
├── main.py
├── config.py
├── requirements.txt
└── README.md
```

The project is separated into handlers, services, database operations, and utility modules to keep the application easier to maintain and extend.

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/75tv7vvcrh-ops/steam_deal_bot.git
cd steam_deal_bot
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file and add your bot token:

```env
BOT_TOKEN=your_bot_token
```

## ▶️ Run

```bash
python main.py
```

## 🧠 Architecture

The bot uses an asynchronous architecture based on **Aiogram 3**.

Main responsibilities are separated between:

* `handlers` — Telegram commands, messages and callbacks
* `services` — application logic and external API interaction
* `database` — SQLite operations
* `utils` — reusable helper functions

This structure allows individual parts of the bot to be modified without putting all application logic into a single file.

## 📌 Project Status

The project is actively used as a practical Python project and development portfolio.

Future improvements may include further optimization of scheduled tasks, persistent caching, and additional API integrations.

## 👨‍💻 Author

**Dokar**

Python Developer focused on building useful software.
