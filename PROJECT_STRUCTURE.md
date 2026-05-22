# 📁 Project Structure — MarketSentry (Modular v3)

## Overview
Automated cryptocurrency arbitrage monitoring system with a **modular architecture**, **real-time price engine**, and **interactive Telegram controls**.

---

## 🏗️ Folder Structure

### 🛠️ Core (`core/`)
Internal systems and engine components.
| File | Purpose |
|------|---------|
| `config.py` | Runtime-mutable configuration (thresholds, job toggles) |
| `engine.py` | High-speed real-time price engine (Dual-thread polling) |
| `database.py` | SQLite history management for APY tracking |

### 🧠 Services (`services/`)
Business logic and market data extraction.
| File | Purpose |
|------|---------|
| `arbitrage.py` | APY math and order book depth logic |
| `indicators.py` | Macro scrapers (VIX, P/E, Fear & Greed, USD/THB, VT drawdown) |
| `signals.py` | Signal state manager (cooldowns, confirmation ticks) |

### 🤖 Bot Layer (`bot/`)
Telegram interface and message handling.
| File | Purpose |
|------|---------|
| `handlers.py` | Command and Background Job logic |
| `formatters.py` | Beautiful HTML message templates |

### 🚀 Entry & Deployment
| File | Purpose |
|------|---------|
| `main.py` | **Entry point** — Bot initialization and startup |
| `Dockerfile` | Docker image configuration |
| `requirements.txt` | Python dependencies |
| `.env` | Secrets (Telegram token, Binance keys) |

---

## 📱 Telegram Commands

### 📋 Info Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message + command list |
| `/apy` | Show current APY + 1h/4h momentum |
| `/rate` | Show BTC funding rate status |
| `/vix` | Show Stock Market VIX index |
| `/greed` | Show Crypto Fear & Greed Index |
| `/thb` | Show real-time USD/THB rate |
| `/vt` | Show VT ETF Drawdown and suggested action |
| `/report` | Show Daily Market Report on demand |
| `/status` | Show system health — engine, prices, job states |

### ⚙️ Control Commands
| Command | Description |
|---------|-------------|
| `/get` | Show all current thresholds and settings |
| `/set <param> <val>` | Change a threshold (e.g., `/set apy 10`) |
| `/stop <job>` | Pause a monitoring job (e.g., `/stop vix`) |
| `/start_job <job>` | Resume a job (e.g., `/start_job vix`) |

---

## 🔄 Background Jobs
| Job | Interval | Description |
|-----|----------|-------------|
| `arbitrage` | 5s | APY spread monitoring |
| `rate` | 10s | Funding rate change detection |
| `vix` | 60s | VIX index zone tracking |
| `fng` | 3600s | Fear & Greed status changes |
| `pe` | 3600s | World Valuation status changes |
| `vt` | 3600s | VT ETF drawdown status monitoring |
| `daily_report` | Daily (7:00 AM) | Broadcast daily compiled market report |
| `apy_tracker`| 3600s | Saves snapshots to `arbitrage.db` |

---

## ⚡ Performance Guidelines

1. **Zero REST in Loops**: Never make API calls inside a loop. Use batch methods.
2. **Cache-First**: Always read from `core.engine.price_cache`.
3. **Dual-Thread Engine**: Mark prices poll @ 100ms, Spot @ 1s to maximize speed without hitting rate limits.
4. **Smart Signals**: Alerts require **3-tick confirmation** to filter out flash spikes.
