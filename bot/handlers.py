import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
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
    get_polymarket_crypto_events,
    get_vt_drawdown
)
from services.signals import signal_manager
from services.earn import get_dual_investment_positions, scan_dual_investment_targets
from core.database import (
    is_dual_alerted, 
    mark_dual_alerted,
    add_dual_target,
    delete_dual_target,
    get_dual_targets,
    clear_dual_targets,
    is_dual_scanned_alerted,
    mark_dual_scanned_alerted
)
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
    format_vt_signal,
    format_country_pe_signal,
    format_daily_report,
    format_dual_settled,
    format_dual_targets_list,
    format_dual_scan_alert,
    WORLD_PE_STATUS_EMOJI,
    COUNTRY_STATUS_EMOJI,
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
        "🤖 <b>MarketSentry Active Sentinel</b>\n\n"
        "<b>📊 Market & Arbitrage:</b>\n"
        "  /apy — Show current spot-futures APY spreads\n"
        "  /rate — Show BTC funding rate status\n"
        "  /maxpain — Show BTC Options Max Pain targets\n"
        "  /earn — Show active Dual Investment contracts (alerts auto-fire on settlement)\n"
        "  /dual — Manage Dual Investment scanner watch notes (add/del/list/scan)\n\n"
        "<b>🌍 Macro & Sentiment:</b>\n"
        "  /vix — Show Stock Market VIX index\n"
        "  /pe — Show World P/E Ratio & trends\n"
        "  /countries — Show P/E rankings for 40+ countries\n"
        "  /greed — Show Crypto Fear & Greed index\n"
        "  /thb — Show real-time USD/THB exchange rate\n"
        "  /poly [limit] — Show Polymarket crypto prediction odds\n"
        "  /vt — Show VT ETF Drawdown & DCA action\n"
        "  /report — Show Daily Market Report on demand\n\n"
        "<b>⚙️ Bot Control & Health:</b>\n"
        "  /status — System health, price latency & job status\n"
        "  /get — View all runtime parameters & settings\n"
        "  /set &lt;param&gt; &lt;value&gt; — Adjust threshold at runtime\n"
        "  /arb on|off — Enable / disable arbitrage monitoring (default: off)\n"
        "  /stop &lt;job&gt; — Pause a background monitoring job\n"
        "  /start_job &lt;job&gt; — Resume a background job\n"
        "  /h — Show this help menu\n\n"
        "<b>📝 Settable Params:</b> <code>apy</code>, <code>vix_fear</code>, <code>vix_super</code>, <code>cooldown</code>, <code>ticks</code>, <code>thb</code>\n"
        "<b>📝 Background Jobs:</b> <code>arbitrage</code>, <code>rate</code>, <code>vix</code>, <code>pe</code>, <code>fng</code>, <code>apy_tracker</code>, <code>thb</code>, <code>maxpain</code>, <code>vt</code>, <code>daily_report</code>, <code>country_pe</code>, <code>earn</code>, <code>dual_scan</code>"
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

    emoji = WORLD_PE_STATUS_EMOJI.get(data['status'], "🌐")
    
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

    lines = ["🌍 <b>Global P/E Rankings</b>\n"]
    for c in countries:
        icon = "⚪"
        for key, sym in COUNTRY_STATUS_EMOJI.items():
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


async def vt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current VT ETF Drawdown."""
    ath, price, drawdown, timestamp = get_vt_drawdown()
    if ath == 0:
        await update.message.reply_text("📭 Failed to fetch VT data.")
        return
        
    action = "HOLD / Normal DCA"
    if drawdown >= 35:
        action = "INVEST 30%"
    elif drawdown >= 30:
        action = "INVEST 35%"
    elif drawdown >= 20:
        action = "INVEST 25%"
        
    text = (
        f"🌎 <b>Vanguard Total World Stock (VT)</b>\n\n"
        f"  📉 Drawdown from ATH: <b>{drawdown:.2f}%</b>\n"
        f"  💰 Current Price: <code>${price:.2f}</code>\n"
        f"  🏔️ All-Time High: <code>${ath:.2f}</code>\n\n"
        f"  💡 <b>Suggested Action:</b> {action}\n\n"
        f"⏰ Last Updated: {timestamp} (Bangkok)"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def earn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active Dual Investment positions and contract amounts."""
    active = get_dual_investment_positions(status='PURCHASE_SUCCESS', limit=50)
    
    if not active:
        await update.message.reply_text("📭 No active Dual Investment contracts found.")
        return

    lines = ["💰 <b>Active Dual Investment Contracts</b>\n"]
    for pos in active:
        lines.append(format_dual_settled(pos))
        lines.append("")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


def parse_target_line(line: str) -> Optional[Tuple[str, float, float, str]]:
    """
    Parses a single target line note like:
    'btc 60000 10 buylow' -> ('BTC', 60000.0, 10.0, 'BUYLOW')
    """
    parts = line.strip().split()
    if len(parts) < 4:
        return None

    coin = parts[0].upper().replace("$", "")
    
    raw_strike = parts[1].replace(",", "").replace("$", "")
    try:
        strike = float(raw_strike)
    except ValueError:
        return None

    raw_apr = parts[2].replace("%", "")
    try:
        min_apr = float(raw_apr)
    except ValueError:
        return None

    raw_opt = parts[3].lower().replace("_", "").replace("-", "")
    if raw_opt in ("buylow", "put", "buy", "low"):
        opt_type = "BUYLOW"
    elif raw_opt in ("sellhigh", "call", "sell", "high"):
        opt_type = "SELLHIGH"
    else:
        return None

    return (coin, strike, min_apr, opt_type)


async def dual_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /dual — Manage Dual Investment watch targets & view current notes.
    """
    text = update.message.text or ""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    if not lines:
        targets = get_dual_targets()
        await update.message.reply_text(format_dual_targets_list(targets), parse_mode=ParseMode.HTML)
        return

    first_line_parts = lines[0].split(maxsplit=1)
    first_arg_str = first_line_parts[1].strip() if len(first_line_parts) > 1 else ""

    # Check single-line subcommands
    if len(lines) == 1:
        if not first_arg_str or first_arg_str.lower() in ("list", "show", "get"):
            targets = get_dual_targets()
            await update.message.reply_text(format_dual_targets_list(targets), parse_mode=ParseMode.HTML)
            return

        if first_arg_str.lower() in ("scan", "check", "run"):
            await update.message.reply_text("🔎 Scanning Dual Investment market for watch targets...", parse_mode=ParseMode.HTML)
            matches = scan_dual_investment_targets()
            if not matches:
                await update.message.reply_text("📭 No matching Dual Investment contracts found right now.", parse_mode=ParseMode.HTML)
                return
            for item in matches:
                msg = format_dual_scan_alert(item["target"], item["product"], item["apr"], item["strike"])
                await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            return

        if first_arg_str.lower() == "clear":
            count = clear_dual_targets()
            await update.message.reply_text(f"🗑️ Cleared <b>{count}</b> watch target note(s).", parse_mode=ParseMode.HTML)
            return

        if first_arg_str.lower().startswith(("del ", "delete ", "remove ", "rm ")):
            parts = first_arg_str.split()
            if len(parts) >= 2 and parts[1].isdigit():
                target_id = int(parts[1])
                success = delete_dual_target(target_id)
                if success:
                    await update.message.reply_text(f"✅ Deleted watch note <code>#{target_id}</code>.", parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text(f"❌ Target note <code>#{target_id}</code> not found.", parse_mode=ParseMode.HTML)
                return

    # Process notes to add
    lines_to_parse = []
    if len(lines) == 1:
        arg_to_parse = first_arg_str
        if arg_to_parse.lower().startswith("add "):
            arg_to_parse = arg_to_parse[4:].strip()
        lines_to_parse.append(arg_to_parse)
    else:
        if first_arg_str and first_arg_str.lower() != "add":
            lines_to_parse.append(first_arg_str)
        lines_to_parse.extend(lines[1:])

    added_targets = []
    failed_lines = []

    for line in lines_to_parse:
        parsed = parse_target_line(line)
        if parsed:
            coin, strike, apr, opt_type = parsed
            tid = add_dual_target(coin, strike, apr, opt_type)
            added_targets.append((tid, coin, strike, apr, opt_type))
        else:
            failed_lines.append(line)

    if added_targets:
        res_lines = [f"✅ Added <b>{len(added_targets)}</b> watch note(s):\n"]
        for tid, coin, strike, apr, opt_type in added_targets:
            badge = "🟢 Buy Low" if "buy" in opt_type.lower() or "put" in opt_type.lower() else "🔴 Sell High"
            res_lines.append(f"  📌 <code>#{tid}</code> | <b>{coin}</b> ${strike:,.2f} | APR ≥ <b>{apr}%</b> | {badge}")
        
        if failed_lines:
            res_lines.append("\n⚠️ <b>Could not parse:</b>")
            for fl in failed_lines:
                res_lines.append(f"  • <code>{fl}</code>")
            res_lines.append("\n💡 <i>Format: <code>&lt;coin&gt; &lt;strike&gt; &lt;min_apr&gt; &lt;buylow|sellhigh&gt;</code></i>")
            res_lines.append("🪙 <i>Example symbols: <code>BTC</code>, <code>ETH</code>, <code>BNB</code>, <code>SOL</code>, <code>XRP</code>, <code>DOGE</code>, <code>SUI</code></i>")

        await update.message.reply_text("\n".join(res_lines), parse_mode=ParseMode.HTML)
    else:
        if failed_lines:
            err_msg = (
                "❌ <b>Could not parse watch target notes.</b>\n\n"
                "<b>Example format:</b>\n"
                "<code>btc 60000 10 buylow</code>\n"
                "<code>eth 1700 15 buylow</code>\n"
                "<code>eth 2500 3 sellhigh</code>\n"
                "<code>sol 180 20 sellhigh</code>\n\n"
                "🪙 <b>Example symbols:</b> <code>BTC</code>, <code>ETH</code>, <code>BNB</code>, <code>SOL</code>, <code>XRP</code>, <code>DOGE</code>, <code>ADA</code>, <code>AVAX</code>, <code>LINK</code>, <code>NEAR</code>, <code>SUI</code>"
            )
            await update.message.reply_text(err_msg, parse_mode=ParseMode.HTML)
        else:
            targets = get_dual_targets()
            await update.message.reply_text(format_dual_targets_list(targets), parse_mode=ParseMode.HTML)


async def dual_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut command: /dual_add <notes>"""
    await dual_command(update, context)


async def dual_del_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut command: /dual_del <id>"""
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("❌ Usage: <code>/dual_del &lt;id&gt;</code>", parse_mode=ParseMode.HTML)
        return
    tid = int(args[0])
    success = delete_dual_target(tid)
    if success:
        await update.message.reply_text(f"✅ Deleted watch note <code>#{tid}</code>.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ Target note <code>#{tid}</code> not found.", parse_mode=ParseMode.HTML)



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
            "<b>Available jobs:</b> arbitrage, rate, vix, pe, fng, apy_tracker, thb, maxpain, vt, daily_report, country_pe, earn, dual_scan"
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
            "<b>Available jobs:</b> arbitrage, rate, vix, pe, fng, apy_tracker, thb, maxpain, vt, daily_report, country_pe, earn, dual_scan"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    job_name = args[0].lower()
    result = BotConfig.set_job(job_name, enabled=True)
    await update.message.reply_text(result, parse_mode=ParseMode.HTML)


async def arb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/arb on|off — Toggle arbitrage monitoring on or off."""
    args = context.args
    if not args or args[0].lower() not in ("on", "off"):
        current = BotConfig.job_enabled.get("arbitrage", False)
        icon = "\U0001f7e2" if current else "\U0001f534"
        status = "Running" if current else "Stopped"
        text = (
            f"{icon} <b>Arbitrage Monitoring:</b> {status}\n\n"
            "Usage:\n"
            "  <code>/arb on</code>  — Start watching for APY spreads\n"
            "  <code>/arb off</code> — Stop arbitrage monitoring"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return

    enable = args[0].lower() == "on"
    result = BotConfig.set_job("arbitrage", enabled=enable)
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
            
        if abs(futures_price - spot_price) < 5.0:
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

    data, _ = get_world_pe_ratio()
    if not data:
        return
        
    signal = signal_manager.check_pe_signal(data['pe'], data['status'])
    if signal:
        message = format_pe_signal(signal, history=data)
        await send_alert(context, message)


async def country_pe_job(context: ContextTypes.DEFAULT_TYPE):
    """Check per-country P/E status changes."""
    if not BotConfig.job_enabled.get("country_pe", True):
        return

    countries, _ = get_all_countries_pe()
    if not countries:
        return

    changes = signal_manager.check_country_pe_signals(countries)
    if changes:
        message = format_country_pe_signal(changes)
        await send_alert(context, message)


async def fng_job(context: ContextTypes.DEFAULT_TYPE):
    """Check Fear & Greed index."""
    if not BotConfig.job_enabled.get("fng", True):
        return

    val, status, _ = get_fear_and_greed_index()
    signal = signal_manager.check_fng_signal(val, status)
    if signal:
        message = format_fng_signal(signal)
        await send_alert(context, message)


async def thb_job(context: ContextTypes.DEFAULT_TYPE):
    """Check USD/THB rate and fire on threshold crossover."""
    if not BotConfig.job_enabled.get("thb", True):
        return

    rate, timestamp = get_usd_thb_rate()
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


async def vt_job(context: ContextTypes.DEFAULT_TYPE):
    """Check VT drawdown."""
    if not BotConfig.job_enabled.get("vt", True):
        return

    ath, price, drawdown, timestamp = get_vt_drawdown()
    if ath == 0:
        return

    signal = signal_manager.check_vt_signal(drawdown)
    if signal:
        message = format_vt_signal(signal, ath, price)
        await send_alert(context, message)


async def earn_job(context: ContextTypes.DEFAULT_TYPE):
    """Check for settled Dual Investment positions."""
    if not BotConfig.job_enabled.get("earn", True):
        return

    positions = get_dual_investment_positions(status='SETTLED', limit=100)
    for pos in positions:
        pos_id = str(pos.get('id'))
        
        # If already alerted, skip
        if is_dual_alerted(pos_id):
            continue
            
        settle_ms = pos.get('settleDate', 0)
        import time
        now_ms = time.time() * 1000
        
        # If the position settled more than 24 hours ago, mark it silently to avoid spam
        # 24 hours = 86400000 ms
        if (now_ms - settle_ms) > 86400000:
            mark_dual_alerted(pos_id)
            continue
            
        # It's a recently settled position, send an alert!
        message = "🔔 <b>Dual Investment Settled!</b>\n\n" + format_dual_settled(pos)
        await send_alert(context, message)
        mark_dual_alerted(pos_id)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show daily report on demand."""
    vix_val, _ = get_vix_index()
    thb_rate, _ = get_usd_thb_rate()
    vt_ath, vt_price, vt_drawdown, _ = get_vt_drawdown()
    fng_val, fng_status, _ = get_fear_and_greed_index()
    pe_data, _ = get_world_pe_ratio()

    message = format_daily_report(
        vix_val=vix_val,
        thb_rate=thb_rate,
        vt_ath=vt_ath,
        vt_price=vt_price,
        vt_drawdown=vt_drawdown,
        fng_val=fng_val,
        fng_status=fng_status,
        pe_data=pe_data
    )

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def daily_report_job(context: ContextTypes.DEFAULT_TYPE):
    """Daily market report at 7:00 AM."""
    if not BotConfig.job_enabled.get("daily_report", True):
        return

    vix_val, _ = get_vix_index()
    thb_rate, _ = get_usd_thb_rate()
    vt_ath, vt_price, vt_drawdown, _ = get_vt_drawdown()
    fng_val, fng_status, _ = get_fear_and_greed_index()
    pe_data, _ = get_world_pe_ratio()

    message = format_daily_report(
        vix_val=vix_val,
        thb_rate=thb_rate,
        vt_ath=vt_ath,
        vt_price=vt_price,
        vt_drawdown=vt_drawdown,
        fng_val=fng_val,
        fng_status=fng_status,
        pe_data=pe_data
    )

    await send_alert(context, message)


async def dual_scan_job(context: ContextTypes.DEFAULT_TYPE):
    """Check Binance Dual Investment market against saved target watch notes."""
    if not BotConfig.job_enabled.get("dual_scan", True):
        return

    try:
        matches = scan_dual_investment_targets()
    except Exception as e:
        logger.error(f"Error in dual_scan_job: {e}")
        return

    for item in matches:
        target = item["target"]
        product = item["product"]
        apr = item["apr"]
        strike = item["strike"]

        prod_id = str(product.get("id") or product.get("orderId") or "0")
        target_id = target["id"]
        settle_date = str(product.get("settleDate") or product.get("deliveryDate") or "0")
        alert_key = f"dual_scan_{target_id}_{prod_id}_{settle_date}"

        if is_dual_scanned_alerted(alert_key):
            continue

        message = format_dual_scan_alert(target, product, apr, strike)
        await send_alert(context, message)
        mark_dual_scanned_alerted(alert_key)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
