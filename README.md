# 🛡️ MarketSentry

An advanced, real-time cryptocurrency arbitrage monitoring and macro-indicator tracking engine. Built with a modular Python architecture, high-speed cached polling, and an interactive Telegram interface.

MarketSentry acts as a 24/7 sentinel—monitoring micro-level exchange price differences, funding rates, options max pain points, and macro economic indicators (like VIX, Fear & Greed, and Polymarket signals) to deliver actionable alerts and live control.

---

## 🌟 Key Features

*   **⚡ Dual-Threaded Price Engine**: Runs dedicated polling threads for mark prices (100ms) and spot prices (1s), utilizing a smart cache to avoid Binance API rate limits.
*   **📊 Spread & Funding Rate Monitor**: Calculates real-time spot-futures APY spreads and tracks funding rate trends.
*   **🌍 Macro Market Sentiment**: Scrapes and tracks the Stock Market Volatility Index (VIX), World P/E Ratios, and the Crypto Fear & Greed Index.
*   **🧠 Prediction & Options Metrics**: Integrates Polymarket crypto prediction market outcomes and monitors option Max Pain price targets.
*   **🌎 VT ETF Drawdown Sentinel**: Tracks Vanguard Total World Stock ETF (VT) drawdown from its all-time high and provides tier-based investment advice.
*   **🌅 Scheduled Market Reports**: Delivers a daily compiled report of VIX, USD/THB, VT, Fear & Greed, and World P/E directly to your chat at 7:00 AM.
*   **⚙️ Runtime-Mutable Controls**: Control jobs (start/stop) and adjust alert thresholds directly from Telegram without restarting the engine.
*   **💾 Database Integration**: Persists historical APY, USD/THB, and Option Max Pain snapshots to an SQLite database for trend analysis.

---

## 🏗️ Folder Structure

*   📁 **`core/`**: Core engine components.
    *   `engine.py` — High-speed dual-threaded Binance polling engine.
    *   `config.py` — Thread-safe, runtime-mutable configurations.
    *   `database.py` — SQLite database interactions for tracking historical metrics.
*   📁 **`services/`**: Scrapers and analytical layers.
    *   `arbitrage.py` — Mathematical models for APY spread calculations.
    *   `indicators.py` — Multi-source scrapers (VIX, P/E, Fear & Greed, USD/THB, Polymarket, Max Pain).
    *   `signals.py` — Alert state management and cooldown mechanisms.
*   📁 **`bot/`**: Telegram interface layer.
    *   `handlers.py` — User command controllers and background job handlers.
    *   `formatters.py` — Beautiful, clean HTML message styling for Telegram.

---

## 🚀 Setup & Installation

### Prerequisites
*   Python 3.8+
*   Telegram Bot Token (via [@BotFather](https://t.me/BotFather))
*   Binance API credentials (optional, fallback to public endpoints is supported)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/bot_arbitrage.git
cd bot_arbitrage

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
```

### 3. Running the Bot
```bash
python main.py
```

### 4. Deploying with Docker
You can also run MarketSentry in a Docker container:
```bash
# Build the container
docker-compose build

# Start in background
docker-compose up -d
```

---

## 📱 Telegram Commands

### Info & Metrics
*   `/start` or `/h` — Display welcome message and commands menu.
*   `/apy` — View current spot-futures APY spreads and averages (1h/4h).
*   `/rate` — Check BTC funding rates.
*   `/vix` — Check global Stock Volatility (VIX).
*   `/pe` — Check World Market P/E Ratio.
*   `/countries` — View P/E Rankings across global countries.
*   `/greed` — Fetch Crypto Fear & Greed Index score.
*   `/thb` — Check real-time USD/THB exchange rates.
*   `/maxpain` — View BTC Option Max Pain price targets.
*   `/poly [limit]` — Fetch live Polymarket crypto prediction odds.
*   `/vt` — Show VT ETF price, all-time high, drawdown percentage, and suggested investment action.
*   `/report` — Show the daily macro market report on demand.
*   `/status` — View system health, live prices, poll rates, and engine status.

### Settings & Job Control
*   `/get` — Retrieve all current system thresholds and running jobs.
*   `/set <param> <value>` — Change thresholds at runtime (e.g., `/set apy 10`).
*   `/stop <job>` — Pause a specific background job (e.g., `/stop vix`).
*   `/start_job <job>` — Resume a background job (e.g., `/start_job vix`).

---

## ⚡ Performance & Safety Defaults
1.  **Cache-First**: The database and command handlers read from `core.engine.price_cache` to ensure instant response times.
2.  **Smart Alert Signals**: Alert triggers require a **3-tick confirmation** to prevent sending alerts on transient price spikes.
3.  **Strict Cooldowns**: Alerts have configurable cooldowns to prevent Telegram message spam.
