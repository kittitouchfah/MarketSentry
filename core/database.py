import sqlite3
import os
import time
from datetime import datetime
from typing import Optional

# Keep the database file in the root directory for easy persistence
DB_PATH = "arbitrage.db"

def init_db():
    """Initializes the SQLite database and creates the tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table to store APY snapshots
    # symbol: the futures contract (e.g., BTCUSD_240628)
    # apy: the annualized yield at the time of the snapshot
    # timestamp: unix timestamp of the snapshot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apy_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            apy REAL NOT NULL,
            timestamp INTEGER NOT NULL
        )
    ''')
    
    # Create index for faster querying by symbol and timestamp
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
        ON apy_history(symbol, timestamp)
    ''')
    
    # Table for THB history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS thb_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rate REAL NOT NULL,
            timestamp INTEGER NOT NULL
        )
    ''')

    # Table for Max Pain history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS max_pain_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency TEXT NOT NULL,
            max_pain REAL NOT NULL,
            timestamp INTEGER NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def save_apy_snapshot(symbol: str, apy: float):
    """Saves a new APY snapshot to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO apy_history (symbol, apy, timestamp)
        VALUES (?, ?, ?)
    ''', (symbol, apy, int(time.time())))
    conn.commit()
    conn.close()

def get_apy_averages(symbol: str) -> dict:
    """
    Calculates the 1-hour and 4-hour moving averages for a given symbol.
    Returns a dict: {"1h": float or None, "4h": float or None}
    """
    now = int(time.time())
    one_hour_ago = now - 3600
    four_hours_ago = now - (4 * 3600)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1-hour average
    cursor.execute('''
        SELECT AVG(apy) FROM apy_history 
        WHERE symbol = ? AND timestamp >= ?
    ''', (symbol, one_hour_ago))
    avg_1h = cursor.fetchone()[0]
    
    # 4-hour average
    cursor.execute('''
        SELECT AVG(apy) FROM apy_history 
        WHERE symbol = ? AND timestamp >= ?
    ''', (symbol, four_hours_ago))
    avg_4h = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "1h": round(avg_1h, 2) if avg_1h is not None else None,
        "4h": round(avg_4h, 2) if avg_4h is not None else None
    }

def save_thb_snapshot(rate: float):
    """Saves a new THB rate snapshot."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO thb_history (rate, timestamp) VALUES (?, ?)', (rate, int(time.time())))
    conn.commit()
    conn.close()

def get_thb_24h_change() -> Optional[float]:
    """Returns the percentage change in THB rate over the last 24 hours."""
    now = int(time.time())
    day_ago = now - 86400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the rate from ~24h ago
    cursor.execute('SELECT rate FROM thb_history WHERE timestamp >= ? ORDER BY timestamp ASC LIMIT 1', (day_ago,))
    old_row = cursor.fetchone()
    
    # Get the latest rate
    cursor.execute('SELECT rate FROM thb_history ORDER BY timestamp DESC LIMIT 1')
    new_row = cursor.fetchone()
    
    conn.close()
    
    if old_row and new_row and old_row[0] > 0:
        return ((new_row[0] - old_row[0]) / old_row[0]) * 100
    return None

def save_max_pain_snapshot(currency: str, max_pain: float):
    """Saves a new Max Pain snapshot."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO max_pain_history (currency, max_pain, timestamp) VALUES (?, ?, ?)', (currency, max_pain, int(time.time())))
    conn.commit()
    conn.close()

def get_max_pain_24h_change(currency: str) -> Optional[float]:
    """Returns the absolute change in Max Pain price over the last 24 hours."""
    now = int(time.time())
    day_ago = now - 86400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT max_pain FROM max_pain_history WHERE currency = ? AND timestamp >= ? ORDER BY timestamp ASC LIMIT 1', (currency, day_ago))
    old_row = cursor.fetchone()
    
    cursor.execute('SELECT max_pain FROM max_pain_history WHERE currency = ? ORDER BY timestamp DESC LIMIT 1', (currency,))
    new_row = cursor.fetchone()
    
    conn.close()
    
    if old_row and new_row:
        return new_row[0] - old_row[0]
    return None

def cleanup_old_data():
    """Deletes records older than 7 days to keep the database small."""
    seven_days_ago = int(time.time()) - (7 * 24 * 3600)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM apy_history WHERE timestamp < ?', (seven_days_ago,))
    cursor.execute('DELETE FROM thb_history WHERE timestamp < ?', (seven_days_ago,))
    cursor.execute('DELETE FROM max_pain_history WHERE timestamp < ?', (seven_days_ago,))
    conn.commit()
    conn.close()

# Initialize DB on module load
init_db()
