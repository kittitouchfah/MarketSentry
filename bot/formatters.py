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
        "Expensive": "⚠️",
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
    """Format a USD/THB rate alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    emoji = "📈" if signal['direction'] == "above" else "📉"
    return (
        f"🇹🇭 <b>USD/THB Rate Alert</b>\n"
        f"\n"
        f"  {emoji} Rate is now <b>{signal['direction'].upper()}</b> threshold\n"
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


