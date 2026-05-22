import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from core.config import BotConfig
from core.engine import engine, price_cache, SUPPORTED_COINS
from core.database import (
    save_apy_snapshot, 
    get_apy_averages, 
    save_thb_snapshot, 
    get_thb_24h_change,
    save_max_pain_snapshot,
    get_max_pain_24h_change
)
from services.arbitrage import funding_rate, calculate_apy_from_cache
from services.indicators import (
    get_vix_index, 
    get_world_pe_ratio, 
    get_all_countries_pe, 
    get_fear_and_greed_index, 
    get_usd_thb_rate,
    get_all_max_pain,
    get_polymarket_crypto_events
)
from services.signals import signal_manager
from bot.formatters import (
    format_apy_signal,
    format_funding_signal,
    format_vix_signal,
    format_pe_signal,
    format_fng_signal,
    format_thb_signal,
    format_max_pain_list,
    format_max_pain_signal,
    format_polymarket_list,
    thailand_tz
)

logger = logging.getLogger(__name__)
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

# ══════════════════════════════════════════════════════════════════
#  Helper
# ══════════════════════════════════════════════════════════════════

async def send_alert(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send a Telegram message with HTML formatting."""
    await context.bot.send_message(
        chat_id=CHAT_ID, text=message, parse_mode=ParseMode.HTML
    )


# ══════════════════════════════════════════════════════════════════
#  User Commands
# ══════════════════════════════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with available commands."""
    text = (
        "🤖 <b>MarketSentry Active</b>\n\n"
        "<b>📋 Commands:</b>\n"
        "  /apy — Show current APY for all coins\n"
        "  /rate — Show BTC funding rate\n"
        "  /vix — Show VIX index\n"
        "  /pe — Show World P/E Ratio & History\n"
        "  /countries — Show P/E for all countries\n"
        "  /greed — Show Crypto Fear & Greed Index\n"
        "  /thb — Show real-time USD/THB exchange rate\n"
        "  /maxpain — Show BTC Options Max Pain\n"
        "  /poly [num] — Show Polymarket Crypto Predictions\n"
        "  /h — Show this help message\n\n"
        "<b>⚙️ Controls:</b>\n"
        "  /get — Show all current settings\n"
        "  /set &lt;param&gt; &lt;value&gt; — Change a setting\n"
        "  /stop &lt;job&gt; — Pause a monitoring job\n"
        "  /start_job &lt;job&gt; — Resume a monitoring job\n"
        "  /status — Show system health\n\n"
        "<b>📝 Settable params:</b> apy, vix_fear, vix_super, cooldown, ticks, thb\n"
        "<b>📝 Jobs:</b> arbitrage, rate, vix, pe, fng, apy_tracker, thb, maxpain"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def apy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current APY for all tracked coins — uses live cache (instant)."""
    futures_prices = price_cache.get_all_futures()
    if not futures_prices:
        await update.message.reply_text("📭 No APY data available. Engine may be starting...")
        return

    lines = ["📊 <b>Current APY Spread</b>\n"]
    found = False
    for symbol, futures_price in sorted(futures_prices.items()):
        if '_PERP' in symbol:
            continue
        base_coin = None
        for prefix, base in SUPPORTED_COINS.items():
            if prefix in symbol:
                base_coin = base
                break
        if not base_coin:
            continue
        spot_price = price_cache.get_spot(base_coin)
        if not spot_price:
            continue
        apy = calculate_apy_from_cache(symbol, base_coin, spot_price, futures_price)
        if apy is None:
            continue
        found = True
        
        # Get historical context
        history = get_apy_averages(symbol)
        h_str = ""
        if history['1h'] or history['4h']:
            parts = []
            if history['1h']: parts.append(f"1h: {history['1h']}%")
            if history['4h']: parts.append(f"4h: {history['4h']}%")
            h_str = f" ({', '.join(parts)})"
        
        emoji = "🔴" if apy > 30 else "🟡" if apy > 15 else "🟢" if apy > BotConfig.apy_threshold else "⚪"
        lines.append(f"  {emoji} <code>{symbol}</code>  <b>{apy:.2f}%</b> {h_str}")

    if not found:
        await update.message.reply_text("📭 No APY data available.")
        return

    lines.append(f"\n⚙️ Alert threshold: {BotConfig.apy_threshold}%")
    
    # Use actual data timestamp from cache
    data_time = price_cache.last_update_str
    lines.append(f"\n⏰ Last Updated: {data_time} (Bangkok)")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current BTC funding rate."""
    rate, time_str = funding_rate()
    emoji = "📈" if rate > 0 else "📉"
    text = (
        f"{emoji} <b>BTC Funding Rate</b>\n\n"
        f"  Rate: <code>{rate:.4f}%</code>\n"
        f"  Status: <b>{signal_manager.funding_status.upper()}</b>\n"
        f"  Next Reset: {time_str}\n\n"
        f"⏰ Last Updated: {price_cache.last_update_str} (Bangkok)"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def vix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current VIX index."""
    vix_val, time_str = get_vix_index()
    if vix_val > BotConfig.vix_super_fear:
        emoji, label = "🔥", "SUPER FEAR"
    elif vix_val > BotConfig.vix_fear:
        emoji, label = "😰", "FEAR"
    else:
        emoji, label = "😌", "NORMAL"

    text = (
        f"📉 <b>VIX Index</b>\n\n"
        f"  {emoji} Status: <b>{label}</b>\n"
        f"  Value: <code>{vix_val:.2f}</code>\n"
        f"  Market Time: {time_str}\n\n"
        f"  Fear: {BotConfig.vix_fear} | Super Fear: {BotConfig.vix_super_fear}\n\n"
        f"⏰ Last Updated: {time_str} (Bangkok)"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def pe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current World P/E Ratio with History and Trends."""
    data, timestamp = get_world_pe_ratio()
    if not data:
        await update.message.reply_text("📭 No P/E data available.")
        return

    status_emoji = {
        "Undervalued": "💎",
        "Fairly Valued": "⚖️",
        "Overvalued": "⚠️",
        "Bubble": "💥",
        "Expensive": "⚠️",
    }
    emoji = status_emoji.get(data['status'], "🌐")
    
    text = (
        f"🌍 <b>World Market Valuation</b>\n\n"
        f"  {emoji} Status: <b>{data['status']}</b>\n"
        f"  Current P/E: <code>{data['pe']:.2f}</code>\n\n"
        f"📊 <b>Historical Averages:</b>\n"
        f"  Last 10Y: <code>{data['pe_10y']:.2f}</code>\n"
        f"  Last 20Y: <code>{data['pe_20y']:.2f}</code>\n\n"
        f"📈 <b>Trend Margins:</b>\n"
        f"  Long Term (SMA200): <b>{data['trend_long']}</b>\n"
        f"  Short Term (SMA50): <b>{data['trend_short']}</b>\n\n"
        f"⏰ Last Updated: {timestamp} (Bangkok)\n"
        f"<i>Data via worldperatio.com</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def countries_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show P/E for all countries, sorted by valuation."""
    await update.message.reply_text("🔎 Fetching global valuation data...")
    # Sort by P/E descending
    countries, timestamp = get_all_countries_pe()
    if not countries:
        await update.message.reply_text("📭 No data available.")
        return

    countries.sort(key=lambda x: x['pe'], reverse=True)

    status_icons = {
        "Cheap": "💎",
        "Fair": "⚖️",
        "Overvalued": "⚠️",
        "Expensive": "🔥",
        "Bubble": "💥",
    }

    lines = ["🌍 <b>Global P/E Rankings</b>\n"]
    for c in countries:
        icon = "⚪"
        for key, sym in status_icons.items():
            if key in c['status']:
                icon = sym
                break
        lines.append(f"  {icon} <b>{c['pe']:.1f}</b> — <code>{c['country']}</code>")
    
    lines.append(f"\n⏰ Last Updated: {timestamp} (Bangkok)")
    full_text = "\n".join(lines)
    if len(full_text) < 4000:
        await update.message.reply_text(full_text, parse_mode=ParseMode.HTML)
    else:
        mid = len(lines) // 2
        await update.message.reply_text("\n".join(lines[:mid]), parse_mode=ParseMode.HTML)
        await update.message.reply_text("\n".join(lines[mid:]), parse_mode=ParseMode.HTML)


async def greed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Crypto Fear & Greed Index."""
    val, status, timestamp = get_fear_and_greed_index()
    if "greed" in status.lower():
        emoji = "🤑"
    elif "fear" in status.lower():
        emoji = "😱"
    else:
        emoji = "😐"
        
    text = (
        f"🧭 <b>Crypto Sentiment</b>\n\n"
        f"  {emoji} Status: <b>{status}</b>\n"
        f"  Index Score: <code>{val}/100</code>\n\n"
        f"⏰ Last Updated: {timestamp} (Bangkok)"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def thb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show real-time USD/THB exchange rate."""
    rate, timestamp = get_usd_thb_rate()
    if rate > 0:
        change_24h = get_thb_24h_change()
        change_str = f" ({change_24h:+.2f}%)" if change_24h is not None else ""
        text = (
            f"🇹🇭 <b>Real-Time USD/THB:</b> <code>{rate:.2f} ฿</code>{change_str}\n\n"
            f"⏰ Last Updated: {timestamp} (Bangkok)"
        )
    else:
        text = "📭 Failed to fetch USD/THB rate."
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def maxpain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Max Pain prices for all expirations."""
    max_pains, timestamp = get_all_max_pain()
    spot_price = price_cache.get_spot("BTC")
    
    if not max_pains or not spot_price:
        await update.message.reply_text("📭 No Max Pain or Spot data available.")
        return
    
    # Get 24h change for the nearest expiration
    nearest_exp = list(max_pains.keys())[0]
    change_24h = get_max_pain_24h_change("BTC")
    change_str = f" (24h Change: {change_24h:+,g})" if change_24h is not None else ""
        
    text = format_max_pain_list(max_pains, spot_price, timestamp)
    if change_str:
        text = text.replace("Expirations:</b>", f"Expirations:</b>\n  ⚡ Nearest Expiration Change: <b>{change_str}</b>")
        
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def poly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Polymarket crypto predictions."""
    limit = 10
    if context.args:
        try:
            limit = int(context.args[0])
            limit = max(1, min(limit, 50))  # Cap between 1 and 50
        except ValueError:
            pass
            
    events, timestamp = get_polymarket_crypto_events(limit=limit)
    
    if not events:
        await update.message.reply_text("📭 No Polymarket data available right now.")
        return
        
    text = format_polymarket_list(events, timestamp)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════════
#  Interactive Control Commands
# ══════════════════════════════════════════════════════════════════

async def get_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/get — Show all current settings and job status."""
    text = BotConfig.get_all()
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def set_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/set <param> <value> — Change a threshold at runtime."""
    args = context.args
    if not args or len(args) < 2:
        text = (
            "❌ Usage: <code>/set &lt;param&gt; &lt;value&gt;</code>\n\n"
            "<b>Available params:</b>\n"
        )
        for name, (_, _, desc) in BotConfig.SETTABLE.items():
            val = getattr(BotConfig, BotConfig.SETTABLE[name][0])
            text += f"  <code>{name}</code> = {val}  ({desc})\n"
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    param_name = args[0].lower()
    param_value = args[1]
    result = BotConfig.set_param(param_name, param_value)
    await update.message.reply_text(result, parse_mode=ParseMode.HTML)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stop <job> — Pause a monitoring job."""
    args = context.args
    if not args:
        text = (
            "❌ Usage: <code>/stop &lt;job&gt;</code>\n\n"
            "<b>Available jobs:</b> arbitrage, rate, vix, pe, fng, apy_tracker, thb, maxpain"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    job_name = args[0].lower()
    result = BotConfig.set_job(job_name, enabled=False)
    await update.message.reply_text(result, parse_mode=ParseMode.HTML)


async def start_job_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start_job <job> — Resume a monitoring job."""
    args = context.args
    if not args:
        text = (
            "❌ Usage: <code>/start_job &lt;job&gt;</code>\n\n"
            "<b>Available jobs:</b> arbitrage, rate, vix, pe, fng, apy_tracker, thb, maxpain"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    job_name = args[0].lower()
    result = BotConfig.set_job(job_name, enabled=True)
    await update.message.reply_text(result, parse_mode=ParseMode.HTML)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status — Show system health."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")

    engine_icon = "🟢" if engine.is_connected else "🔴"
    engine_status = "Connected" if engine.is_connected else "Disconnected"
    stats = price_cache.stats()
    mark_age = f"{stats['mark_age_ms']}ms" if stats['mark_age_ms'] is not None else "N/A"
    spot_age = f"{stats['spot_age_ms']}ms" if stats['spot_age_ms'] is not None else "N/A"

    spot_lines = []
    for _, base in SUPPORTED_COINS.items():
        price = price_cache.get_spot(base)
        if price:
            spot_lines.append(f"    {base}: ${price:,.2f}")

    lines = [
        f"🏥 <b>System Status</b>",
        f"",
        f"  {engine_icon} Price Engine: <b>{engine_status}</b>",
        f"  🕐 Server Time: {now}",
        f"",
        f"  🇹🇭 USD/THB Rate: <b>{get_usd_thb_rate()[0]:.2f} ฿</b>",
        f"",
        f"  ⚡ <b>Poll Rates (of 6,000/min budget):</b>",
        f"    {engine.poll_rate_summary}",
        f"",
        f"  📡 <b>Cache Age:</b>",
        f"    Mark Prices: <code>{mark_age}</code>",
        f"    Spot Prices: <code>{spot_age}</code>",
        f"",
    ]

    if spot_lines:
        lines.append("  💰 <b>Live Prices:</b>")
        lines.extend(spot_lines)
        lines.append("")

    lines.append("  🔄 <b>Jobs:</b>")
    for job, enabled in BotConfig.job_enabled.items():
        icon = "🟢" if enabled else "🔴"
        status = "Running" if enabled else "Stopped"
        lines.append(f"    {icon} {job}: {status}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════════
#  Background Jobs
# ══════════════════════════════════════════════════════════════════

async def arbitrage_job(context: ContextTypes.DEFAULT_TYPE):
    """Check APY using live price cache and fire smart signals."""
    if not BotConfig.job_enabled.get("arbitrage", True):
        return

    futures_prices = price_cache.get_all_futures()

    for symbol, futures_price in futures_prices.items():
        base_coin = None
        for prefix, base in SUPPORTED_COINS.items():
            if prefix in symbol:
                base_coin = base
                break
        if not base_coin or '_PERP' in symbol:
            continue

        spot_price = price_cache.get_spot(base_coin)
        if not spot_price:
            continue

        apy = calculate_apy_from_cache(symbol, base_coin, spot_price, futures_price)
        if apy is None:
            continue

        signal = signal_manager.check_apy_signal(symbol, apy)
        if signal:
            history = get_apy_averages(symbol)
            message = format_apy_signal(signal, spot=spot_price, futures=futures_price, history=history)
            await send_alert(context, message)


async def rate_job(context: ContextTypes.DEFAULT_TYPE):
    """Check funding rate."""
    if not BotConfig.job_enabled.get("rate", True):
        return

    rate = price_cache.get_funding("BTCUSD_PERP")
    if rate is None:
        rate_data = funding_rate()
        rate = rate_data[0]

    signal = signal_manager.check_funding_signal("BTCUSD_PERP", rate)
    if signal:
        message = format_funding_signal(signal)
        await send_alert(context, message)


async def vix_job(context: ContextTypes.DEFAULT_TYPE):
    """Check VIX."""
    if not BotConfig.job_enabled.get("vix", True):
        return

    vix_val, _ = get_vix_index()
    signal = signal_manager.check_vix_signal(vix_val)
    if signal:
        message = format_vix_signal(signal)
        await send_alert(context, message)


async def pe_job(context: ContextTypes.DEFAULT_TYPE):
    """Check World P/E."""
    if not BotConfig.job_enabled.get("pe", True):
        return

    data = get_world_pe_ratio()
    if not data:
        return
        
    signal = signal_manager.check_pe_signal(data['pe'], data['status'])
    if signal:
        message = format_pe_signal(signal, history=data)
        await send_alert(context, message)


async def fng_job(context: ContextTypes.DEFAULT_TYPE):
    """Check Fear & Greed index."""
    if not BotConfig.job_enabled.get("fng", True):
        return

    val, status = get_fear_and_greed_index()
    signal = signal_manager.check_fng_signal(val, status)
    if signal:
        message = format_fng_signal(signal)
        await send_alert(context, message)


async def thb_job(context: ContextTypes.DEFAULT_TYPE):
    """Check USD/THB rate and fire on threshold crossover."""
    if not BotConfig.job_enabled.get("thb", True):
        return

    rate = get_usd_thb_rate()
    if rate <= 0:
        return

    signal = signal_manager.check_thb_signal(rate)
    if signal:
        message = format_thb_signal(signal)
        await send_alert(context, message)
    
    # Save snapshot for history
    save_thb_snapshot(rate)


async def maxpain_job(context: ContextTypes.DEFAULT_TYPE):
    """Check if Spot price crosses the nearest Max Pain point."""
    if not BotConfig.job_enabled.get("maxpain", True):
        return
        
    max_pains, timestamp = get_all_max_pain()
    spot_price = price_cache.get_spot("BTC")
    
    if not max_pains or not spot_price:
        return
        
    # Get the nearest expiration date
    nearest_exp = list(max_pains.keys())[0]
    nearest_price = max_pains[nearest_exp]
    
    signal = signal_manager.check_max_pain_signal(spot_price, nearest_price, nearest_exp)
    if signal:
        message = format_max_pain_signal(signal)
        await send_alert(context, message)

    # Save snapshot for history
    save_max_pain_snapshot("BTC", nearest_price)


async def apy_tracker_job(context: ContextTypes.DEFAULT_TYPE):
    """Logs APY to SQLite every hour."""
    if not BotConfig.job_enabled.get("apy_tracker", True):
        return
        
    futures_prices = price_cache.get_all_futures()
    for symbol, futures_price in futures_prices.items():
        if '_PERP' in symbol:
            continue
        base_coin = None
        for prefix, base in SUPPORTED_COINS.items():
            if prefix in symbol:
                base_coin = base
                break
        if not base_coin:
            continue
        
        spot_price = price_cache.get_spot(base_coin)
        if not spot_price:
            continue
            
        apy = calculate_apy_from_cache(symbol, base_coin, spot_price, futures_price)
        if apy is not None:
            save_apy_snapshot(symbol, apy)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
