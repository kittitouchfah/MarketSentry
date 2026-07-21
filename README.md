# 🛡️ MarketSentry

An advanced, real-time cryptocurrency arbitrage monitoring and macro-indicator tracking engine. Built with a modular Python architecture, high-speed cached polling, and an interactive Telegram interface.

MarketSentry acts as a 24/7 sentinel—monitoring micro-level exchange price differences, funding rates, options max pain points, macro economic indicators (like VIX, Fear & Greed, and Polymarket signals), and Binance Dual Investment contract settlements to deliver actionable alerts and live control.

---

## 🌟 Key Features

*   **⚡ Dual-Threaded Price Engine**: Runs dedicated polling threads for mark prices (2s) and spot prices (5s), utilizing a smart cache to avoid Binance API rate limits (~42 req/min of 2,400 limit).
*   **📊 Spread & Funding Rate Monitor**: Calculates real-time spot-futures APY spreads and tracks funding rate trends with 3-tick confirmation to eliminate false alerts.
*   **💰 Dual Investment Tracker**: Monitors Binance Dual Investment contracts — auto-alerts on settlement within 24h, shows all active contracts with live spot prices (including WBETH and other wrapped tokens).
*   **🌍 Macro Market Sentiment**: Scrapes and tracks the Stock Market Volatility Index (VIX), World P/E Ratios (global + 40+ countries), and the Crypto Fear & Greed Index.
*   **🧠 Prediction & Options Metrics**: Integrates Polymarket crypto prediction market outcomes and monitors BTC Option Max Pain price targets.
*   **🌎 VT ETF Drawdown Sentinel**: Tracks Vanguard Total World Stock ETF (VT) drawdown from its all-time high and provides tier-based DCA investment advice.
*   **🇹🇭 USD/THB Monitor**: Real-time USD/THB exchange rate tracking with threshold crossover alerts.
*   **🌅 Scheduled Market Reports**: Delivers a daily compiled report of VIX, USD/THB, VT, Fear & Greed, and World P/E directly to your chat at 7:00 AM Bangkok time.
*   **⚙️ Runtime-Mutable Controls**: Control jobs (start/stop) and adjust alert thresholds directly from Telegram without restarting the engine.
*   **💾 Database Integration**: Persists historical APY, USD/THB, Option Max Pain snapshots, and Dual Investment alert state to an SQLite database for trend analysis and deduplication.

---

## 🏗️ Folder Structure

*   📁 **`core/`**: Core engine components.
    *   `engine.py` — High-speed dual-threaded Binance polling engine with `PriceCache`.
    *   `config.py` — Thread-safe, runtime-mutable configurations and job toggles.
    *   `database.py` — SQLite database interactions for APY, THB, Max Pain & Dual Investment alert tracking.
*   📁 **`services/`**: Scrapers and analytical layers.
    *   `arbitrage.py` — Mathematical models for APY spread calculations and order book depth.
    *   `indicators.py` — Multi-source scrapers (VIX, P/E, Fear & Greed, USD/THB, Polymarket, Max Pain, VT ETF).
    *   `signals.py` — Alert state management and cooldown mechanisms with tick confirmation.
    *   `earn.py` — Binance Dual Investment position fetcher via signed REST API.
*   📁 **`bot/`**: Telegram interface layer.
    *   `handlers.py` — User command controllers and background job handlers.
    *   `formatters.py` — Beautiful HTML message templates with centralized `WORLD_PE_STATUS_EMOJI` and `COUNTRY_STATUS_EMOJI` maps, and `get_live_spot_price()` helper.

---

## 🚀 Setup & Installation

### Prerequisites
*   Python 3.8+
*   Telegram Bot Token (via [@BotFather](https://t.me/BotFather))
*   Binance API credentials (read-only, for Dual Investment & price data)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/MarketSentry.git
cd MarketSentry

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
```bash
# Build and start in background
docker-compose up -d --build
```

---

## 📱 Telegram Commands

### 📊 Market & Arbitrage
*   `/apy` — View current spot-futures APY spreads and averages (1h/4h).
*   `/rate` — Check BTC funding rate.
*   `/maxpain` — View BTC Option Max Pain price targets for all expirations.
*   `/earn` — Show all active Dual Investment contracts with live spot prices. Auto-alerts fire on settlement.

### 🌍 Macro & Sentiment
*   `/vix` — Check global Stock Volatility (VIX).
*   `/pe` — Check World Market P/E Ratio with historical context.
*   `/countries` — View P/E rankings across 40+ global countries.
*   `/greed` — Fetch Crypto Fear & Greed Index score.
*   `/thb` — Check real-time USD/THB exchange rates.
*   `/poly [limit]` — Fetch live Polymarket crypto prediction odds.
*   `/vt` — Show VT ETF price, all-time high, drawdown percentage, and suggested DCA action.
*   `/report` — Show the daily macro market report on demand.

### ⚙️ Settings & Job Control
*   `/status` — View system health, live prices, poll rates, and engine status.
*   `/get` — Retrieve all current system thresholds and running jobs.
*   `/set <param> <value>` — Change thresholds at runtime (e.g., `/set apy 10`).
*   `/stop <job>` — Pause a specific background job (e.g., `/stop vix`).
*   `/start_job <job>` — Resume a background job (e.g., `/start_job vix`).
*   `/h` — Show help menu.

**Settable params:** `apy`, `vix_fear`, `vix_super`, `cooldown`, `ticks`, `thb`

---

## 🔄 Background Jobs
| Job | Interval | Description |
|-----|----------|-------------|
| `arbitrage` | 5s | APY spread monitoring |
| `rate` | 10s | Funding rate change detection |
| `vix` | 60s | VIX index zone tracking |
| `thb` | 60s | USD/THB crossover alerts |
| `earn` | 600s | Dual Investment settlement detection |
| `apy_tracker` | 600s | Saves APY snapshots to `arbitrage.db` |
| `fng` | 3600s | Fear & Greed status changes |
| `pe` | 3600s | World Valuation status changes |
| `country_pe` | 3600s | Per-country P/E status change alerts |
| `vt` | 3600s | VT ETF drawdown status monitoring |
| `maxpain` | 3600s | BTC Options Max Pain crossover alerts |
| `daily_report` | Daily 7AM BKK | Broadcast compiled daily market report |

---

## ⚡ Performance & Safety Defaults
1.  **Cache-First**: The command handlers read from `core.engine.price_cache` to ensure instant response times.
2.  **Smart Alert Signals**: Alert triggers require a **3-tick confirmation** to prevent sending alerts on transient price spikes.
3.  **Strict Cooldowns**: Alerts have configurable cooldowns to prevent Telegram message spam.
4.  **Live REST for Earn**: `get_live_spot_price()` in `formatters.py` fetches directly from Binance REST API to support any asset (including WBETH and other wrapped tokens not in the main price cache).
5.  **Dual Investment Deduplication**: All alerted position IDs are persisted in SQLite to prevent duplicate settlement notifications across bot restarts.
