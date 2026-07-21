# 📁 Project Structure — MarketSentry (Modular v3)

## Overview
Automated cryptocurrency arbitrage monitoring system with a **modular architecture**, **real-time price engine**, **Binance Dual Investment tracker**, and **interactive Telegram controls**.

---

## 🏗️ Folder Structure

### 🛠️ Core (`core/`)
Internal systems and engine components.
| File | Purpose |
|------|---------|
| `config.py` | Runtime-mutable configuration (thresholds, job toggles) |
| `engine.py` | High-speed real-time price engine (Dual-thread polling) |
| `database.py` | SQLite history management for APY, THB, Max Pain & Dual Investment alert tracking |

### 🧠 Services (`services/`)
Business logic and market data extraction.
| File | Purpose |
|------|---------|
| `arbitrage.py` | APY math and order book depth logic |
| `indicators.py` | Macro scrapers (VIX, P/E, Fear & Greed, USD/THB, VT drawdown, Max Pain, Polymarket) |
| `signals.py` | Signal state manager (cooldowns, confirmation ticks) |
| `earn.py` | Binance Dual Investment position fetcher (signed REST API) |

### 🤖 Bot Layer (`bot/`)
Telegram interface and message handling.
| File | Purpose |
|------|---------|
| `handlers.py` | Command and Background Job logic |
| `formatters.py` | Beautiful HTML message templates with centralized status emoji maps |

### 🚀 Entry & Deployment
| File | Purpose |
|------|---------|
| `main.py` | **Entry point** — Bot initialization and startup |
| `Dockerfile` | Docker image configuration |
| `docker-compose.yml` | Docker Compose deployment |
| `requirements.txt` | Python dependencies |
| `.env` | Secrets (Telegram token, Binance keys) |

---

## 📱 Telegram Commands

### 📊 Market & Arbitrage
| Command | Description |
|---------|-------------|
| `/apy` | Show current spot-futures APY spreads + 1h/4h momentum |
| `/rate` | Show BTC funding rate status |
| `/maxpain` | Show BTC Options Max Pain targets for all expirations |
| `/earn` | Show all active Dual Investment contracts with live prices |

### 🌍 Macro & Sentiment
| Command | Description |
|---------|-------------|
| `/vix` | Show Stock Market VIX index |
| `/pe` | Show World P/E Ratio & historical trends |
| `/countries` | Show P/E rankings for 40+ countries |
| `/greed` | Show Crypto Fear & Greed Index |
| `/thb` | Show real-time USD/THB exchange rate |
| `/poly [limit]` | Show Polymarket crypto prediction odds |
| `/vt` | Show VT ETF Drawdown and suggested DCA action |
| `/report` | Show Daily Market Report on demand |

### ⚙️ Control Commands
| Command | Description |
|---------|-------------|
| `/status` | System health — engine, prices, job states |
| `/get` | Show all current thresholds and settings |
| `/set <param> <val>` | Change a threshold at runtime (e.g., `/set apy 10`) |
| `/stop <job>` | Pause a monitoring job (e.g., `/stop vix`) |
| `/start_job <job>` | Resume a job (e.g., `/start_job vix`) |
| `/h` | Show this help menu |

---

## 🔄 Background Jobs
| Job | Interval | Description |
|-----|----------|-------------|
| `arbitrage` | 5s | APY spread monitoring & alerts |
| `rate` | 10s | Funding rate change detection |
| `vix` | 60s | VIX index zone tracking |
| `thb` | 60s | USD/THB rate crossover alerts |
| `fng` | 3600s | Fear & Greed status changes |
| `pe` | 3600s | World Valuation status changes |
| `country_pe` | 3600s | Per-country P/E status change alerts |
| `vt` | 3600s | VT ETF drawdown status monitoring |
| `maxpain` | 3600s | BTC Options Max Pain crossover alerts |
| `earn` | 600s | Dual Investment settlement detection & alerts |
| `apy_tracker` | 600s | Saves APY snapshots to `arbitrage.db` |
| `daily_report` | Daily (7:00 AM BKK) | Broadcast compiled daily market report |

---

## 🎨 Centralized Emoji Status Maps (`bot/formatters.py`)

### World P/E (`WORLD_PE_STATUS_EMOJI`)
| Status | Emoji |
|--------|-------|
| Undervalued | 💎 |
| Fairly Valued | ⚖️ |
| Overvalued | ⚠️ |
| Expensive | 🔥 |
| Bubble | 💥 |

### Country P/E (`COUNTRY_STATUS_EMOJI`)
| Status | Emoji |
|--------|-------|
| Undervalued | 💎 |
| Cheap | 🟢 |
| Fair | ⚖️ |
| Overvalued | ⚠️ |
| Expensive | 🔥 |
| Bubble | 💥 |

---

## ⚡ Performance Guidelines

1. **Zero REST in Hot Loops**: APY/rate/VIX jobs read only from `core.engine.price_cache`.
2. **Cache-First**: Commands read from `price_cache` for instant response (no API latency).
3. **Dual-Thread Engine**: Mark prices @ 2s, Spot prices @ 5s — ~42 req/min total out of 2,400 IP limit.
4. **Smart Signals**: Alerts require **3-tick confirmation** to filter out transient price spikes.
5. **Live REST for Earn**: `format_dual_settled()` fetches real-time spot prices via `get_live_spot_price()` (direct Binance REST) to support non-cached assets like WBETH.
