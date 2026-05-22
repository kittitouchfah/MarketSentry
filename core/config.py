"""
Centralized, runtime-mutable configuration for MarketSentry.

Defaults are loaded from environment variables (or hardcoded fallbacks).
Values can be changed at runtime via Telegram /set commands.
"""

import os
import threading
from typing import Dict
from dotenv import load_dotenv

load_dotenv()


class BotConfig:
    """Thread-safe, runtime-mutable bot configuration."""

    _lock = threading.Lock()

    # ── Thresholds ──────────────────────────────────────────────
    apy_threshold: float = float(os.getenv("APY_THRESHOLD", "7.0"))
    vix_fear: float = float(os.getenv("VIX_FEAR", "30.0"))
    vix_super_fear: float = float(os.getenv("VIX_SUPER_FEAR", "40.0"))
    thb_threshold: float = float(os.getenv("THB_THRESHOLD", "35.0"))

    # ── Cooldowns ───────────────────────────────────────────────
    signal_cooldown_minutes: int = int(os.getenv("SIGNAL_COOLDOWN_MIN", "15"))
    confirmation_ticks: int = int(os.getenv("CONFIRMATION_TICKS", "3"))

    # ── WebSocket / Polling ─────────────────────────────────────
    ws_reconnect_delay: int = 5          # seconds
    fallback_poll_interval: int = 300    # 5 minutes

    # ── Job enabled flags (toggled by /start and /stop) ─────────
    job_enabled: Dict[str, bool] = {
        "arbitrage": True,
        "rate": True,
        "vix": True,
        "pe": True,
        "fng": True,
        "apy_tracker": True,
        "thb": True,
        "maxpain": True,
        "vt": True,
        "daily_report": True,
    }

    # ── Settable parameters map (name → attribute) ──────────────
    SETTABLE = {
        "apy":        ("apy_threshold",         float, "APY alert threshold (%)"),
        "vix_fear":   ("vix_fear",              float, "VIX fear level"),
        "vix_super":  ("vix_super_fear",        float, "VIX super-fear level"),
        "cooldown":   ("signal_cooldown_minutes", int,  "Signal cooldown (minutes)"),
        "ticks":      ("confirmation_ticks",      int,  "Confirmation ticks before alert"),
        "thb":        ("thb_threshold",           float, "USD/THB alert threshold"),
    }

    @classmethod
    def set_param(cls, name: str, value: str) -> str:
        """Set a parameter by name. Returns a confirmation string or error."""
        if name not in cls.SETTABLE:
            valid = ", ".join(cls.SETTABLE.keys())
            return f"❌ Unknown parameter '{name}'.\nValid: {valid}"

        attr, cast, description = cls.SETTABLE[name]
        try:
            parsed = cast(value)
        except (ValueError, TypeError):
            return f"❌ Invalid value '{value}' for {name} (expected {cast.__name__})"

        with cls._lock:
            old = getattr(cls, attr)
            setattr(cls, attr, parsed)

        return f"✅ {description}\n   {old} → {parsed}"

    @classmethod
    def get_all(cls) -> str:
        """Return a formatted string of all current settings."""
        lines = ["⚙️ <b>Current Settings</b>\n"]
        for name, (attr, _, description) in cls.SETTABLE.items():
            val = getattr(cls, attr)
            lines.append(f"  <code>{name}</code> = <b>{val}</b>  ({description})")

        lines.append("\n🔄 <b>Job Status</b>\n")
        for job, enabled in cls.job_enabled.items():
            icon = "🟢" if enabled else "🔴"
            lines.append(f"  {icon} <code>{job}</code> — {'Running' if enabled else 'Stopped'}")

        return "\n".join(lines)

    @classmethod
    def set_job(cls, job_name: str, enabled: bool) -> str:
        """Enable or disable a monitoring job."""
        if job_name not in cls.job_enabled:
            valid = ", ".join(cls.job_enabled.keys())
            return f"❌ Unknown job '{job_name}'.\nValid: {valid}"

        with cls._lock:
            cls.job_enabled[job_name] = enabled

        action = "▶️ Started" if enabled else "⏹️ Stopped"
        return f"{action} <b>{job_name}</b> monitoring"
