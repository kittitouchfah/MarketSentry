"""
Templates for beautiful Telegram messages.
"""

from datetime import datetime
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from core.config import BotConfig

thailand_tz = zoneinfo.ZoneInfo("Asia/Bangkok")


def format_apy_signal(signal: dict, spot: float = None, futures: float = None, history: dict = None) -> str:
    """Format a rich APY alert message."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"📊 <b>Arbitrage Signal</b> — {signal['emoji']} {signal['level']}",
        "",
        f"  Symbol:   <code>{signal['symbol']}</code>",
        f"  APY:      <b>{signal['apy']:.2f}%</b>",
    ]
    if spot and futures:
        spread_pct = ((futures - spot) / spot) * 100
        lines.extend([
            f"  Spot:     ${spot:,.2f}",
            f"  Futures:  ${futures:,.2f}",
            f"  Spread:   {spread_pct:.2f}%",
        ])
    
    if history:
        h1 = history.get('1h')
        h4 = history.get('4h')
        h1_str = f"{h1:.2f}%" if h1 is not None else "N/A"
        h4_str = f"{h4:.2f}%" if h4 is not None else "N/A"
        lines.extend([
            f"",
            f"📈 <b>Momentum:</b>",
            f"  1h Avg:   {h1_str}",
            f"  4h Avg:   {h4_str}",
        ])
        
    lines.extend([
        "",
        f"⏰ Last Updated: {now} (Bangkok)",
    ])
    return "\n".join(lines)


def format_funding_signal(signal: dict) -> str:
    """Format a funding rate change alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    emoji = "📈" if signal['new_status'] == "positive" else "📉"
    return (
        f"🚨 <b>Funding Rate Change</b>\n"
        f"\n"
        f"  {emoji} {signal['old_status'].upper()} → <b>{signal['new_status'].upper()}</b>\n"
        f"  Rate: <code>{signal['rate']:.4f}%</code>\n"
        f"\n"
        f"⏰ Last Updated: {now} (Bangkok)"
    )


def format_vix_signal(signal: dict) -> str:
    """Format a VIX zone change alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    zone_emoji = {"normal": "😌", "fear": "😰", "super_fear": "🔥"}
    emoji = zone_emoji.get(signal['new_status'], "❓")
    return (
        f"📉 <b>VIX Alert</b>\n"
        f"\n"
        f"  {emoji} {signal['old_status'].upper()} → <b>{signal['new_status'].upper()}</b>\n"
        f"  Value: <code>{signal['value']:.2f}</code>\n"
        f"  Fear: {BotConfig.vix_fear} | Super Fear: {BotConfig.vix_super_fear}\n"
        f"\n"
        f"⏰ Last Updated: {now} (Bangkok)"
    )


def format_pe_signal(signal: dict, history: dict = None) -> str:
    """Format a World P/E valuation change alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    status_emoji = {
        "Undervalued": "💎",
        "Fairly Valued": "⚖️",
        "Overvalued": "⚠️",
        "Bubble": "💥",
        "Expensive": "🔥",
    }
    emoji = status_emoji.get(signal['new_status'], "🌐")
    
    lines = [
        f"🌍 <b>World Valuation Alert</b>",
        f"",
        f"  {emoji} {signal['old_status']} → <b>{signal['new_status']}</b>",
        f"  P/E Ratio: <code>{signal['value']:.2f}</code>",
    ]
    
    if history:
        lines.extend([
            f"",
            f"📊 <b>Context:</b>",
            f"  10Y Avg: <code>{history['pe_10y']:.2f}</code>",
            f"  20Y Avg: <code>{history['pe_20y']:.2f}</code>",
            f"  Long-Term Trend: <b>{history['trend_long']}</b>",
        ])
        
    lines.extend([
        f"",
        f"⏰ Last Updated: {now} (Bangkok)",
    ])
    return "\n".join(lines)


# Shared status emoji map used across formatters
COUNTRY_STATUS_EMOJI = {
    "Cheap": "💎",
    "Fair": "⚖️",
    "Overvalued": "⚠️",
    "Expensive": "🔥",
    "Bubble": "💥",
}


def format_country_pe_signal(changes: list) -> str:
    """Format an alert for countries whose P/E status has changed."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "🌍 <b>Country P/E Status Change</b>",
        "",
    ]
    for change in changes:
        old_emoji = COUNTRY_STATUS_EMOJI.get(change['old_status'], "⚪")
        new_emoji = COUNTRY_STATUS_EMOJI.get(change['new_status'], "⚪")
        lines.append(
            f"  <b>{change['country']}</b>  PE: <code>{change['pe']:.1f}</code>"
        )
        lines.append(
            f"    {old_emoji} {change['old_status']} → {new_emoji} <b>{change['new_status']}</b>"
        )
        lines.append("")
    lines.append(f"⏰ Last Updated: {now} (Bangkok)")
    return "\n".join(lines)


def format_fng_signal(signal: dict) -> str:
    """Format a Fear and Greed index alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    status = signal['new_status'].lower()
    if "greed" in status:
        emoji = "🤑"
    elif "fear" in status:
        emoji = "😱"
    else:
        emoji = "😐"
        
    return (
        f"🧭 <b>Crypto Sentiment Shift</b>\n"
        f"\n"
        f"  {emoji} {signal['old_status']} → <b>{signal['new_status']}</b>\n"
        f"  Index Score: <code>{signal['value']}/100</code>\n"
        f"\n"
        f"⏰ Last Updated: {now} (Bangkok)"
    )


def format_thb_signal(signal: dict) -> str:
    """Format a USD/THB rate crossover alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    if signal['direction'] == "above":
        emoji = "📈"
        direction_text = "crossed <b>ABOVE</b> threshold (THB weakening)"
    else:
        emoji = "📉"
        direction_text = "crossed <b>BELOW</b> threshold (THB strengthening)"
    return (
        f"🇹🇭 <b>USD/THB Rate Alert</b>\n"
        f"\n"
        f"  {emoji} Rate has {direction_text}\n"
        f"  Current: <code>{signal['value']:.2f} ฿</code>\n"
        f"  Threshold: <code>{signal['threshold']:.2f} ฿</code>\n"
        f"\n"
        f"⏰ Last Updated: {now} (Bangkok)"
    )



def format_max_pain_list(max_pains: dict, spot_price: float, timestamp: str = None) -> str:
    """Format the list of all Max Pain prices."""
    if not timestamp:
        timestamp = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    
    lines = [
        f"🎯 <b>Options Max Pain (BTC)</b>\n",
        f"  Spot Price: <b>${spot_price:,.2f}</b>\n",
        f"<b>Expirations:</b>"
    ]
    
    for exp, price in max_pains.items():
        diff = ((spot_price - price) / price) * 100
        icon = "🔴" if spot_price < price else "🟢"
        lines.append(f"  {icon} <code>{exp:<9}</code>: <b>${price:,.0f}</b> ({diff:+.2f}%)")
        
    lines.append(f"\n⏰ Last Updated: {timestamp} (Bangkok)")
    return "\n".join(lines)


def format_max_pain_signal(signal: dict) -> str:
    """Format a Max Pain crossover alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    emoji = "🚀" if signal['direction'] == "above" else "📉"
    return (
        f"🎯 <b>Max Pain Crossover Alert</b>\n"
        f"\n"
        f"  {emoji} Spot crossed <b>{signal['direction'].upper()}</b> Max Pain\n"
        f"  Target Expiration: <code>{signal['expiration']}</code>\n"
        f"  Max Pain: <b>${signal['max_pain']:,.2f}</b>\n"
        f"  Spot Price: <b>${signal['spot']:,.2f}</b>\n"
        f"\n"
        f"⏰ Last Updated: {now} (Bangkok)"
    )


def format_polymarket_list(events: list, timestamp: str = None) -> str:
    """Format the list of Polymarket crypto events."""
    if not timestamp:
        timestamp = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
        
    lines = [
        f"🔮 <b>Polymarket Predictions (Crypto)</b>\n"
    ]
    
    for i, e in enumerate(events):
        title = e['title']
        volume = e['volume']
        outcomes = e['outcomes']
        is_featured = e.get('is_featured', False)
        
        # Format volume beautifully (e.g. $1.2M, $500K)
        if volume >= 1_000_000:
            vol_str = f"${volume/1_000_000:.1f}M"
        elif volume >= 1_000:
            vol_str = f"${volume/1_000:.0f}K"
        else:
            vol_str = f"${volume:.0f}"
            
        import html
        safe_title = html.escape(title)
        emoji = "⭐" if is_featured else "🔹"
        lines.append(f"{emoji} <b>{safe_title}</b>")
        lines.append(f"   Vol: <code>{vol_str}</code>")
        
        # Format probabilities: each on its own line for multi-market events
        for name, prob in outcomes:
            safe_name = html.escape(name)
            lines.append(f"   ▫️ {safe_name}: <b>{prob:.0f}%</b>")
        lines.append("")
        
    lines.append(f"⏰ Last Updated: {timestamp} (Bangkok)")
    return "\n".join(lines)


def format_vt_signal(signal: dict, ath: float, price: float) -> str:
    """Format a VT ETF Drawdown alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    drawdown = signal["drawdown"]
    status = signal["new_status"]
    
    action = "HOLD / Normal DCA"
    if status == "drawdown_35":
        action = "INVEST 30%"
    elif status == "drawdown_30":
        action = "INVEST 35%"
    elif status == "drawdown_20":
        action = "INVEST 25%"

    return (
        f"🚨 <b>VT ETF Drawdown Alert</b>\n"
        f"\n"
        f"  📉 Current Drawdown: <b>{drawdown:.2f}%</b>\n"
        f"  💰 Current Price: <code>${price:.2f}</code>\n"
        f"  🏔️ All-Time High: <code>${ath:.2f}</code>\n"
        f"\n"
        f"  💡 <b>Action:</b> {action}\n"
        f"\n"
        f"⏰ Last Updated: {now} (Bangkok)"
    )


def format_daily_report(
    vix_val: float,
    thb_rate: float,
    vt_ath: float,
    vt_price: float,
    vt_drawdown: float,
    fng_val: int,
    fng_status: str,
    pe_data: dict
) -> str:
    """Format the daily 7:00 AM market report."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. VIX status
    if vix_val > BotConfig.vix_super_fear:
        vix_emoji, vix_label = "🔥", "SUPER FEAR"
    elif vix_val > BotConfig.vix_fear:
        vix_emoji, vix_label = "😰", "FEAR"
    else:
        vix_emoji, vix_label = "😌", "NORMAL"
        
    # 2. THB Status
    thb_emoji = "🇹🇭"
    
    # 3. VT suggested action
    vt_action = "HOLD / Normal DCA"
    if vt_drawdown >= 35:
        vt_action = "INVEST 30%"
    elif vt_drawdown >= 30:
        vt_action = "INVEST 35%"
    elif vt_drawdown >= 20:
        vt_action = "INVEST 25%"
        
    # 4. FNG status
    fng_emoji = "😐"
    if fng_status:
        status_lower = fng_status.lower()
        if "greed" in status_lower:
            fng_emoji = "🤑"
        elif "fear" in status_lower:
            fng_emoji = "😱"
            
    # 5. World PE status
    pe_emoji = "🌐"
    pe_val_str = "N/A"
    pe_status_str = "Unknown"
    if pe_data:
        pe_val_str = f"{pe_data.get('pe', 0.0):.2f}"
        pe_status = pe_data.get('status', 'Unknown')
        pe_status_str = pe_status
        status_emoji = {
            "Undervalued": "💎",
            "Fairly Valued": "⚖️",
            "Overvalued": "⚠️",
            "Bubble": "💥",
            "Expensive": "⚠️",
        }
        pe_emoji = status_emoji.get(pe_status, "🌐")

    lines = [
        "🌅 <b>Daily Market Report (7:00 AM)</b>",
        "",
        f"  {vix_emoji} <b>VIX Index:</b> <code>{vix_val:.2f}</code> ({vix_label})",
        f"  {thb_emoji} <b>USD/THB:</b> <code>{thb_rate:.2f} ฿</code>",
        f"  🌎 <b>VT ETF Drawdown:</b> <code>{vt_drawdown:.2f}%</code> (Suggested: <b>{vt_action}</b>)",
        f"  🧭 <b>Crypto Fear & Greed:</b> <code>{fng_val}/100</code> ({fng_status})",
        f"  {pe_emoji} <b>World Market PE:</b> <code>{pe_val_str}</code> ({pe_status_str})",
        "",
        f"⏰ Generated: {now} (Bangkok)"
    ]
    return "\n".join(lines)


