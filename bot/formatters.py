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


# Shared status emoji maps used across formatters and handlers
WORLD_PE_STATUS_EMOJI = {
    "Undervalued": "💎",
    "Fairly Valued": "⚖️",
    "Overvalued": "⚠️",
    "Expensive": "🔥",
    "Bubble": "💥",
}

COUNTRY_STATUS_EMOJI = {
    "Undervalued": "💎",
    "Cheap": "🟢",
    "Fair": "⚖️",
    "Overvalued": "⚠️",
    "Expensive": "🔥",
    "Bubble": "💥",
}


def format_pe_signal(signal: dict, history: dict = None) -> str:
    """Format a World P/E valuation change alert."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
    emoji = WORLD_PE_STATUS_EMOJI.get(signal['new_status'], "🌐")
    
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
    "Undervalued": "💎",
    "Cheap": "🟢",
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


def get_live_spot_price(asset: str) -> float:
    """
    Fetches real-time live spot price directly from Binance REST API.
    Supports any coin (WBETH, BTC, ETH, SOL, BNB, etc.) without relying on price_cache.
    """
    if not asset or asset.upper() in ("USDT", "USDC", "BUSD", "USD", "?"):
        return None

    import requests
    asset_upper = asset.upper()
    for quote in ("USDT", "USDC"):
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={asset_upper}{quote}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                price = float(res.json().get("price", 0))
                if price > 0:
                    return price
        except Exception:
            pass
    return None


def format_dual_settled(position: dict, current_price: float = None) -> str:
    """Format a Dual Investment position alert with real-time live spot price."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")

    asset        = position.get("investCoin") or position.get("depositAsset") or position.get("investAsset") or "?"
    target_price = position.get("exercisedPrice") or position.get("strikePrice") or position.get("strike") or "?"
    apy          = position.get("apr") or position.get("annualPercentageRate") or position.get("apy") or "?"
    settled_coin = position.get("rewardAsset") or position.get("settleCoin") or position.get("rewardCoin") or "?"
    amount       = (
        position.get("amount") or
        position.get("investAmount") or
        position.get("depositAmount") or
        position.get("subscriptionAmount") or
        position.get("purchaseAmount") or
        "?"
    )
    pos_id       = position.get("id") or position.get("orderId") or "?"

    # Determine target coin for real-time live price check via REST API
    if current_price is None:
        target_coin = asset
        if target_coin in ("USDT", "USDC", "BUSD", "?") or not target_coin:
            target_coin = position.get("exercisedCoin") or position.get("settleAsset") or position.get("rewardAsset") or ""
        
        current_price = get_live_spot_price(target_coin)

    # Determine if exercised (converted to other coin) or redeemed (kept original)
    was_exercised = position.get("exercised")
    if was_exercised is None:
        if settled_coin != "?" and asset != "?":
            was_exercised = (settled_coin.upper() != asset.upper())
        else:
            was_exercised = False

    if was_exercised:
        outcome_emoji = "🔄"
        outcome_text  = f"Converted to <b>{settled_coin}</b>"
    else:
        outcome_emoji = "✅"
        outcome_text  = f"Redeemed in <b>{asset}</b>"

    try:
        apy_val = float(apy)
        apy_str = f"{apy_val * 100:.2f}%" if apy_val < 1 else f"{apy_val:.2f}%"
    except (TypeError, ValueError):
        apy_str = str(apy)

    try:
        target_str = f"${float(target_price):,.2f}"
    except (TypeError, ValueError):
        target_str = str(target_price)

    try:
        amt_float = float(amount)
        amount_str = f"{amt_float:,.4f}".rstrip('0').rstrip('.') if '.' in f"{amt_float:,.4f}" else f"{amt_float:,.0f}"
    except (TypeError, ValueError):
        amount_str = str(amount)

    price_line = ""
    if current_price:
        try:
            price_line = f"  📊 Live Price:   <b>${float(current_price):,.2f}</b>\n"
        except (TypeError, ValueError):
            price_line = f"  📊 Live Price:   <b>{current_price}</b>\n"

    settle_ms = position.get("settleDate") or position.get("deliveryDate") or position.get("settlementDate") or 0
    settle_line = ""
    if settle_ms:
        try:
            settle_dt = datetime.fromtimestamp(float(settle_ms) / 1000, tz=thailand_tz)
            now_dt = datetime.now(thailand_tz)
            diff_seconds = (settle_dt - now_dt).total_seconds()
            if diff_seconds > 0:
                days_left = max(0, int(round(diff_seconds / 86400)))
                settle_line = f"  📅 Settle Date:  <b>{settle_dt.strftime('%Y-%m-%d %H:%M')} ({days_left} days left)</b>\n"
            else:
                settle_line = f"  📅 Settle Date:  <b>{settle_dt.strftime('%Y-%m-%d %H:%M')} (Settled)</b>\n"
        except Exception:
            pass

    return (
        f"💰 <b>Dual Investment Position</b>\n"
        f"\n"
        f"  {outcome_emoji} Outcome: {outcome_text}\n"
        f"  🪙 Asset: <code>{asset}</code>  Amount: <code>{amount_str}</code>\n"
        f"  🎯 Target Price: <b>{target_str}</b>\n"
        f"{price_line}"
        f"{settle_line}"
        f"  📈 APY Earned: <b>{apy_str}</b>\n"
        f"  🆔 Position: <code>{pos_id}</code>"
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
        pe_emoji = WORLD_PE_STATUS_EMOJI.get(pe_status, "🌐")

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


def format_dual_targets_list(targets: list) -> str:
    """Format active Dual Investment watch targets in a clean note style."""
    if not targets:
        return (
            "📝 <b>Dual Investment Watch Notes</b>\n\n"
            "📭 <i>No active watch targets set.</i>\n\n"
            "💡 <b>Add targets via note format:</b>\n"
            "<code>/dual add</code>\n"
            "<code>btc 60000 10 buylow</code>\n"
            "<code>eth 1700 15 buylow</code>\n"
            "<code>eth 2500 3 sellhigh</code>\n"
            "<code>sol 180 20 sellhigh</code>\n\n"
            "🪙 <b>Example symbols:</b> <code>BTC</code>, <code>ETH</code>, <code>BNB</code>, <code>SOL</code>, <code>XRP</code>, <code>DOGE</code>, <code>ADA</code>, <code>AVAX</code>, <code>LINK</code>, <code>NEAR</code>, <code>SUI</code>"
        )

    lines = ["📝 <b>Dual Investment Watch Notes</b>\n"]
    for t in targets:
        opt_type = t['option_type'].lower()
        badge = "🟢 Buy Low" if "buy" in opt_type or "put" in opt_type else "🔴 Sell High"
        lines.append(
            f"  📌 <code>#{t['id']}</code> | <b>{t['coin']}</b> ${t['strike_price']:,.2f} | "
            f"APR ≥ <b>{t['min_apr']}%</b> | {badge}"
        )

    lines.extend([
        "",
        "🪙 <i>Example symbols: <code>BTC</code>, <code>ETH</code>, <code>BNB</code>, <code>SOL</code>, <code>XRP</code>, <code>DOGE</code>, <code>SUI</code></i>",
        "🔎 <i>To scan now: <code>/dual scan</code></i>",
        "💡 <i>To add: <code>/dual add &lt;coin&gt; &lt;strike&gt; &lt;min_apr&gt; &lt;buylow|sellhigh&gt;</code></i>",
        "💡 <i>To delete: <code>/dual del &lt;id&gt;</code></i>",
        "💡 <i>To clear all: <code>/dual clear</code></i>"
    ])
    return "\n".join(lines)



def format_dual_scan_alert(target: dict, product: dict, apr: float, strike: float) -> str:
    """Format alert message when a Dual Investment target condition is matched."""
    now = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")

    coin = target['coin'].upper()
    opt_raw = target['option_type'].lower()
    if "buy" in opt_raw or "put" in opt_raw:
        type_str = "Buy Low (PUT)"
        type_emoji = "🟢"
    else:
        type_str = "Sell High (CALL)"
        type_emoji = "🔴"

    settle_ms = product.get("settleDate") or product.get("deliveryDate") or 0
    settle_str = "N/A"
    if settle_ms:
        try:
            settle_dt = datetime.fromtimestamp(settle_ms / 1000, tz=thailand_tz)
            now_dt = datetime.now(thailand_tz)
            diff_seconds = (settle_dt - now_dt).total_seconds()
            days_left = max(0, int(round(diff_seconds / 86400)))
            settle_str = f"{settle_dt.strftime('%Y-%m-%d %H:%M')} ({days_left} days)"
        except Exception:
            pass

    prod_id = product.get("id") or product.get("orderId") or "N/A"

    return (
        f"🎯 <b>Dual Investment Target Matched!</b>\n\n"
        f"  {type_emoji} <b>Type:</b> {type_str}\n"
        f"  🪙 <b>Coin:</b> <code>{coin}</code>\n"
        f"  🎯 <b>Target Strike:</b> <b>${strike:,.2f}</b>\n"
        f"  📈 <b>Current APR:</b> <b>{apr:.2f}%</b> (Target: ≥ {target['min_apr']:.1f}%)\n"
        f"  📅 <b>Settle Date:</b> {settle_str}\n"
        f"  🆔 <b>Product ID:</b> <code>{prod_id}</code>\n\n"
        f"⏰ Alert Time: {now} (Bangkok)"
    )





