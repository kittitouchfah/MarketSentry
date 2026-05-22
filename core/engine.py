"""
High-speed real-time price engine.

Uses TWO parallel background threads to maximize update frequency:
  - Thread 1 (FAST): Mark prices + funding rates every 100ms  → 600 req/min
  - Thread 2 (SLOW): Spot prices every 1s                     → 60  req/min
  Total: ~660 req/min out of 6,000 allowed (11% of rate limit)
"""

import os
import logging
import threading
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from binance.client import Client
from binance.cm_futures import CMFutures
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
thailand_tz = zoneinfo.ZoneInfo("Asia/Bangkok")

# Binance API clients
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")
client = Client(api_key, api_secret)
cm_futures_client = CMFutures(key=api_key, secret=api_secret)


class PriceCache:
    """Thread-safe in-memory price store."""

    def __init__(self):
        self._lock = threading.Lock()
        self._spot: Dict[str, float] = {}          # e.g. {"BTC": 104230.5}
        self._futures: Dict[str, float] = {}       # e.g. {"BTCUSD_260926": 108120.0}
        self._funding_rate: Dict[str, float] = {}  # e.g. {"BTCUSD_PERP": 0.01}
        self._last_mark_update: float = 0.0
        self._last_spot_update: float = 0.0

    def update_spot(self, symbol: str, price: float):
        with self._lock:
            self._spot[symbol] = price
            self._last_spot_update = time.time()

    def update_futures(self, symbol: str, price: float):
        with self._lock:
            self._futures[symbol] = price
            self._last_mark_update = time.time()

    def update_funding(self, symbol: str, rate: float):
        with self._lock:
            self._funding_rate[symbol] = rate

    def get_spot(self, symbol: str):
        with self._lock:
            return self._spot.get(symbol)

    def get_futures(self, symbol: str):
        with self._lock:
            return self._futures.get(symbol)

    def get_funding(self, symbol: str):
        with self._lock:
            return self._funding_rate.get(symbol)

    def get_all_futures(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._futures)

    @property
    def last_update(self) -> float:
        return max(self._last_mark_update, self._last_spot_update)

    @property
    def last_update_str(self) -> str:
        ts = self.last_update
        if ts == 0:
            return "Never"
        dt = datetime.fromtimestamp(ts, tz=thailand_tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def stats(self) -> Dict[str, Any]:
        """Return latency stats for /status command."""
        now = time.time()
        return {
            "mark_age_ms": round((now - self._last_mark_update) * 1000, 1) if self._last_mark_update else None,
            "spot_age_ms": round((now - self._last_spot_update) * 1000, 1) if self._last_spot_update else None,
        }


# Global price cache instance
price_cache = PriceCache()

# Supported coins mapping: futures prefix → spot base
SUPPORTED_COINS = {
    "BTCUSD": "BTC",
    "ETHUSD": "ETH",
    "XRPUSD": "XRP",
    "BNBUSD": "BNB",
    "SOLUSD": "SOL",
}

# ── Polling intervals ──────────────────────────────────────────────
MARK_POLL_INTERVAL = 0.1   # seconds (600 mark updates/min)
SPOT_POLL_INTERVAL = 1.0   # seconds (60 spot updates/min)


class PriceEngine:
    """
    High-speed dual-thread price engine.

    Thread 1 — Mark prices + funding rates (every 100ms)
    Thread 2 — Spot prices (every 1s, slower since spot is more stable)
    """

    def __init__(self):
        self._running = False
        self._mark_thread: Optional[threading.Thread] = None
        self._spot_thread: Optional[threading.Thread] = None
        self._futures_symbols: Set[str] = set()
        self._mark_connected = False
        self._spot_connected = False

    def start(self):
        """Start both price update threads."""
        if self._running:
            logger.warning("PriceEngine already running")
            return

        # Fetch available futures symbols once at startup
        self._futures_symbols = set(self._fetch_futures_symbols())
        logger.info(f"PriceEngine tracking {len(self._futures_symbols)} futures symbols")

        self._running = True

        # Thread 1: fast mark price loop (100ms)
        self._mark_thread = threading.Thread(
            target=self._mark_loop, daemon=True, name="MarkPriceThread"
        )
        self._mark_thread.start()

        # Thread 2: spot price loop (1s)
        self._spot_thread = threading.Thread(
            target=self._spot_loop, daemon=True, name="SpotPriceThread"
        )
        self._spot_thread.start()

        logger.info(
            f"PriceEngine started — mark@{MARK_POLL_INTERVAL*1000:.0f}ms, "
            f"spot@{SPOT_POLL_INTERVAL*1000:.0f}ms"
        )

    def stop(self):
        """Stop all threads."""
        self._running = False
        self._mark_connected = False
        self._spot_connected = False
        for t in [self._mark_thread, self._spot_thread]:
            if t:
                t.join(timeout=5)
        logger.info("PriceEngine stopped")

    @property
    def is_connected(self) -> bool:
        return self._mark_connected and self._spot_connected and self._running

    @property
    def poll_rate_summary(self) -> str:
        mark_rpm = int(60 / MARK_POLL_INTERVAL)
        spot_rpm = int(60 / SPOT_POLL_INTERVAL)
        total = mark_rpm + spot_rpm
        return (
            f"Mark: {MARK_POLL_INTERVAL*1000:.0f}ms ({mark_rpm}/min) | "
            f"Spot: {SPOT_POLL_INTERVAL*1000:.0f}ms ({spot_rpm}/min) | "
            f"Total: {total}/min of 6,000 budget"
        )

    # ── Thread 1: Fast mark price loop ──────────────────────────

    def _mark_loop(self):
        """Poll mark prices + funding every 100ms."""
        while self._running:
            try:
                self._update_mark_prices()
                self._mark_connected = True
            except Exception as e:
                logger.error(f"Mark price loop error: {e}")
                self._mark_connected = False
                time.sleep(2)
                continue
            time.sleep(MARK_POLL_INTERVAL)

    def _update_mark_prices(self):
        """Fetch all mark prices + funding rates in one API call."""
        all_marks = client.futures_coin_mark_price()
        for item in all_marks:
            symbol = item.get('symbol', '')
            mark = item.get('markPrice')

            # Update futures mark prices (non-perpetual)
            if mark and symbol in self._futures_symbols:
                price_cache.update_futures(symbol, float(mark))

            # Extract funding rates from perpetuals in same response
            if '_PERP' in symbol:
                rate = item.get('lastFundingRate')
                if rate:
                    price_cache.update_funding(symbol, float(rate) * 100)

    # ── Thread 2: Spot price loop ────────────────────────────────

    def _spot_loop(self):
        """Poll spot prices every 1s (spot prices move slower)."""
        while self._running:
            try:
                self._update_spot_prices()
                self._spot_connected = True
            except Exception as e:
                logger.error(f"Spot price loop error: {e}")
                self._spot_connected = False
                time.sleep(2)
                continue
            time.sleep(SPOT_POLL_INTERVAL)

    def _update_spot_prices(self):
        """Batch fetch only the 5 spot prices we need."""
        symbols = [f"{base}USDT" for base in SUPPORTED_COINS.values()]
        # Batch request only the symbols we need - format as JSON string with no spaces
        tickers = client.get_symbol_ticker(symbols=json.dumps(symbols, separators=(',', ':')))
        for t in tickers:
            base = t['symbol'].replace("USDT", "")
            price_cache.update_spot(base, float(t['price']))

    # ── Utilities ────────────────────────────────────────────────

    def _fetch_futures_symbols(self) -> List[str]:
        """Get all non-perpetual coin-margined futures symbols."""
        try:
            info = cm_futures_client.exchange_info()
            return [
                s['symbol'] for s in info['symbols']
                if '_PERP' not in s['symbol']
            ]
        except Exception as e:
            logger.error(f"Error fetching futures symbols: {e}")
            return []


# Global engine instance
engine = PriceEngine()
