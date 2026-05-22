"""
Smart signal state management.
Handles confirmation ticks, cooldowns, and status tracking for all indicators.
"""

import time
import logging
from collections import defaultdict
from typing import Tuple, Dict, Optional, Any
from core.config import BotConfig

logger = logging.getLogger(__name__)

# ── Signal Strength Levels ──────────────────────────────────────

SIGNAL_LEVELS = {
    "LOW":    (7.0, 15.0,  "🟢"),
    "MEDIUM": (15.0, 30.0, "🟡"),
    "HIGH":   (30.0, float('inf'), "🔴"),
}


def classify_signal(apy: float) -> Tuple[str, str]:
    """Returns (level_name, emoji) based on APY value."""
    for level, (low, high, emoji) in SIGNAL_LEVELS.items():
        if low <= apy < high:
            return level, emoji
    if apy >= 30.0:
        return "HIGH", "🔴"
    return "LOW", "🟢"


# ── Signal Manager ──────────────────────────────────────────────

class SignalManager:
    """
    Manages signal state: confirmation ticks, cooldowns, and deduplication.
    Does NOT contain formatting logic (see bot/formatters.py).
    """

    def __init__(self):
        # Track consecutive ticks above threshold per symbol
        self._tick_counts: Dict[str, int] = defaultdict(int)
        # Track last alert timestamp per (event_type, symbol)
        self._last_alert: Dict[str, float] = {}
        # Track funding rate status
        self._funding_status: str = "positive"
        # Track VIX status
        self._vix_status: str = "normal"
        # Track World P/E status
        self._pe_status: str = "Unknown"
        # Track Fear and Greed status
        self._fng_status: str = "Neutral"
        # Track THB rate status (True if above threshold)
        self._thb_above_threshold: Optional[bool] = None
        # Track Max Pain crossover status (True if Spot >= Max Pain)
        self._max_pain_above: Optional[bool] = None

    def check_apy_signal(self, symbol: str, apy: float) -> Optional[Dict[str, Any]]:
        """
        Check if an APY signal should fire.
        Returns a signal dict if conditions are met, else None.
        """
        threshold = BotConfig.apy_threshold

        if apy > threshold:
            self._tick_counts[symbol] += 1
        else:
            self._tick_counts[symbol] = 0
            return None

        # Need enough consecutive ticks
        if self._tick_counts[symbol] < BotConfig.confirmation_ticks:
            return None

        # Check cooldown
        cooldown_key = f"apy:{symbol}"
        if not self._cooldown_passed(cooldown_key):
            return None

        # Fire signal
        self._last_alert[cooldown_key] = time.time()
        self._tick_counts[symbol] = 0  # Reset after firing

        level, emoji = classify_signal(apy)
        return {
            "type": "apy",
            "symbol": symbol,
            "apy": apy,
            "level": level,
            "emoji": emoji,
        }

    def check_funding_signal(self, symbol: str, rate: float) -> Optional[Dict[str, Any]]:
        """Check if funding rate changed sign."""
        new_status = "positive" if rate > 0 else "negative"

        if new_status == self._funding_status:
            return None

        # Check cooldown
        cooldown_key = f"funding:{symbol}"
        if not self._cooldown_passed(cooldown_key):
            return None

        old_status = self._funding_status
        self._funding_status = new_status
        self._last_alert[cooldown_key] = time.time()

        return {
            "type": "funding",
            "symbol": symbol,
            "rate": rate,
            "old_status": old_status,
            "new_status": new_status,
        }

    def check_vix_signal(self, vix_value: float) -> Optional[Dict[str, Any]]:
        """Check if VIX crossed into a new zone."""
        if vix_value > BotConfig.vix_super_fear:
            new_status = "super_fear"
        elif vix_value > BotConfig.vix_fear:
            new_status = "fear"
        else:
            new_status = "normal"

        if new_status == self._vix_status:
            return None

        cooldown_key = "vix"
        if not self._cooldown_passed(cooldown_key):
            return None

        old_status = self._vix_status
        self._vix_status = new_status
        self._last_alert[cooldown_key] = time.time()

        return {
            "type": "vix",
            "value": vix_value,
            "old_status": old_status,
            "new_status": new_status,
        }

    def check_pe_signal(self, pe_val: float, status: str) -> Optional[Dict[str, Any]]:
        """Check if World P/E status changed."""
        if status == self._pe_status:
            return None

        cooldown_key = "world_pe"
        if not self._cooldown_passed(cooldown_key):
            return None

        old_status = self._pe_status
        self._pe_status = status
        self._last_alert[cooldown_key] = time.time()

        return {
            "type": "world_pe",
            "value": pe_val,
            "old_status": old_status,
            "new_status": status,
        }

    def check_fng_signal(self, value: int, status: str) -> Optional[Dict[str, Any]]:
        """Check if Fear and Greed status changed."""
        if status == self._fng_status:
            return None

        cooldown_key = "fng"
        if not self._cooldown_passed(cooldown_key):
            return None

        old_status = self._fng_status
        self._fng_status = status
        self._last_alert[cooldown_key] = time.time()

        return {
            "type": "fng",
            "value": value,
            "old_status": old_status,
            "new_status": status,
        }

    def check_thb_signal(self, rate: float) -> Optional[Dict[str, Any]]:
        """
        Check if USD/THB rate crossed the threshold.
        Returns signal dict on crossover, else None.
        """
        threshold = BotConfig.thb_threshold
        is_above = rate >= threshold

        # Initialize or check for crossover
        if self._thb_above_threshold is None:
            self._thb_above_threshold = is_above
            return None

        if is_above == self._thb_above_threshold:
            return None

        # Check cooldown
        cooldown_key = "thb_alert"
        if not self._cooldown_passed(cooldown_key):
            return None

        self._thb_above_threshold = is_above
        self._last_alert[cooldown_key] = time.time()

        return {
            "type": "thb",
            "value": rate,
            "threshold": threshold,
            "direction": "above" if is_above else "below"
        }

    def check_max_pain_signal(self, spot_price: float, max_pain_price: float, expiration: str) -> Optional[Dict[str, Any]]:
        """
        Check if Spot Price crossed the Max Pain price.
        """
        is_above = spot_price >= max_pain_price

        if self._max_pain_above is None:
            self._max_pain_above = is_above
            return None

        if is_above == self._max_pain_above:
            return None

        cooldown_key = "max_pain_alert"
        if not self._cooldown_passed(cooldown_key):
            return None

        self._max_pain_above = is_above
        self._last_alert[cooldown_key] = time.time()

        return {
            "type": "max_pain",
            "spot": spot_price,
            "max_pain": max_pain_price,
            "expiration": expiration,
            "direction": "above" if is_above else "below"
        }

    def _cooldown_passed(self, key: str) -> bool:
        """Check if enough time has passed since the last alert for this key."""
        last = self._last_alert.get(key, 0)
        cooldown_secs = BotConfig.signal_cooldown_minutes * 60
        return (time.time() - last) >= cooldown_secs

    @property
    def funding_status(self) -> str:
        return self._funding_status

    @property
    def vix_status(self) -> str:
        return self._vix_status

    @property
    def pe_status(self) -> str:
        return self._pe_status

    @property
    def fng_status(self) -> str:
        return self._fng_status


# Global signal manager instance
signal_manager = SignalManager()
