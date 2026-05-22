import os
import logging
import time
from datetime import datetime
from collections import defaultdict
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from binance.client import Client
from binance.cm_futures import CMFutures
from dotenv import load_dotenv

load_dotenv()

# Initialize the client
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

client = Client(api_key, api_secret)
cm_futures_client = CMFutures(key=api_key, secret=api_secret)
thailand_tz = zoneinfo.ZoneInfo("Asia/Bangkok")

# Supported coins mapping for Delivery Futures
SUPPORTED_COINS = {
    'BTCUSD_': 'BTC',
    'ETHUSD_': 'ETH',
    'XRPUSD_': 'XRP',
    'BNBUSD_': 'BNB',
    'SOLUSD_': 'SOL',
}


def get_spread_index():
    """Fetches all futures symbols from Binance that are not perpetuals."""
    try:
        futures_info = cm_futures_client.exchange_info()
        return [
            crypto['symbol']
            for crypto in futures_info['symbols']
            if '_PERP' not in crypto['symbol']
        ]
    except Exception as e:
        logging.error(f"Error fetching spread index: {e}")
        return []


def funding_rate():
    """Fetches the current funding rate for BTC perpetual futures."""
    try:
        funding_data = cm_futures_client.mark_price(symbol='BTCUSD_PERP')
        rate = funding_data[0]['lastFundingRate']
        timestamp = funding_data[0]['time']
        dt_object_local = datetime.fromtimestamp(float(timestamp) / 1000, thailand_tz)
        return [float(rate) * 100, dt_object_local.strftime("%Y-%m-%d %H:%M:%S")]
    except Exception as e:
        logging.error(f"Error fetching funding rate: {e}")
        return [0.0, "N/A"]


def calculate_apy(crypto_symbol, base_coin):
    """Calculates the APY for a given futures symbol and its base coin."""
    try:
        # Extract date from symbol (e.g., BTCUSD_240628 -> 240628)
        parts = crypto_symbol.split('_')
        if len(parts) < 2:
            return None

        date_str = parts[1]
        date_obj = datetime.strptime(date_str, "%y%m%d").replace(tzinfo=thailand_tz)

        # Get current time in same timezone
        current_now = datetime.now(thailand_tz)

        # Calculate days to maturity
        duration = date_obj - current_now
        total_days = duration.total_seconds() / (24 * 3600)

        if total_days <= 0:
            return None

        # Fetch spot price
        ticker = client.get_symbol_ticker(symbol=f"{base_coin}USDT")
        spot_price = float(ticker['price'])

        # Fetch futures price
        mark_price_data = cm_futures_client.mark_price(symbol=crypto_symbol)
        futures_price = float(mark_price_data[0]['markPrice'])

        # Calculate APY
        spread_rate = (futures_price - spot_price) / spot_price
        apy = (spread_rate * 365 * 100) / total_days

        return round(apy, 5)
    except Exception as e:
        logging.error(f"Error calculating APY for {crypto_symbol}: {e}")
        return None


def calculate_apy_from_cache(crypto_symbol, base_coin, spot_price, futures_price):
    """
    Calculates APY using cached prices (from PriceEngine).
    Avoids REST API calls — used for real-time signal checking.
    """
    try:
        parts = crypto_symbol.split('_')
        if len(parts) < 2:
            return None

        date_str = parts[1]
        date_obj = datetime.strptime(date_str, "%y%m%d").replace(tzinfo=thailand_tz)
        current_now = datetime.now(thailand_tz)

        total_days = (date_obj - current_now).total_seconds() / (24 * 3600)
        if total_days <= 0:
            return None

        spread_rate = (futures_price - spot_price) / spot_price
        apy = (spread_rate * 365 * 100) / total_days

        return round(apy, 5)
    except Exception as e:
        logging.error(f"Error calculating cached APY for {crypto_symbol}: {e}")
        return None


def get_order_book_depth(symbol, limit=5):
    """
    Fetch top bids/asks for a futures symbol to estimate executable volume.
    Returns estimated USD liquidity within top `limit` levels.
    """
    try:
        book = cm_futures_client.depth(symbol=symbol, limit=limit)
        bid_volume = sum(float(b[1]) for b in book.get('bids', []))
        ask_volume = sum(float(a[1]) for a in book.get('asks', []))

        # Get mark price for USD conversion
        mark_data = cm_futures_client.mark_price(symbol=symbol)
        mark_price = float(mark_data[0]['markPrice'])

        # Each contract = 100 USD for BTC, 10 USD for others
        contract_value = 100 if 'BTC' in symbol else 10
        bid_usd = bid_volume * contract_value
        ask_usd = ask_volume * contract_value

        return {
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "bid_usd": bid_usd,
            "ask_usd": ask_usd,
            "mark_price": mark_price,
        }
    except Exception as e:
        logging.error(f"Error fetching order book for {symbol}: {e}")
        return None


def spread():
    """Main function to check APY for all supported coins (REST fallback)."""
    spread_apy = defaultdict(list)

    spread_index = get_spread_index()
    logging.info(f"Checking spread for: {spread_index}")

    for crypto in spread_index:
        for prefix, base_coin in SUPPORTED_COINS.items():
            if prefix in crypto:
                apy = calculate_apy(crypto, base_coin)
                if apy is not None:
                    spread_apy['crypto'].append(crypto)
                    spread_apy['apy'].append(apy)
                    logging.info(f"{crypto} APY: {apy}%")
                break

    return spread_apy
