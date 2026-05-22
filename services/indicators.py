import logging
import time
import requests
import json
from datetime import datetime, timedelta
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

# Simple TTL cache
_vix_cache = {"value": None, "time_str": None, "expires": 0}
_pe_cache = {"data": None, "timestamp": None, "expires": 0}
_countries_cache = {"data": None, "timestamp": None, "expires": 0}
_fng_cache = {"value": None, "status": None, "timestamp": None, "expires": 0}
_thb_cache = {"value": None, "timestamp": None, "expires": 0}
_max_pain_cache = {"data": None, "timestamp": None, "expires": 0}
_poly_cache = {"data": None, "timestamp": None, "expires": 0}
_CACHE_TTL = 3600  # 1 hour for indicators
thailand_tz = zoneinfo.ZoneInfo("Asia/Bangkok")


def get_vix_index():
    """Fetches the VIX index value and the last market time from Yahoo Finance. Cached."""
    global _vix_cache

    if _vix_cache["value"] is not None and time.time() < _vix_cache["expires"]:
        return [_vix_cache["value"], _vix_cache["time_str"]]

    try:
        # Add random parameter to bypass cache
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/^VIX?interval=1m&range=1d&_={int(time.time())}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if data and "chart" in data and data["chart"]["result"]:
            res = data["chart"]["result"][0]["meta"]
            price = float(res.get("regularMarketPrice", 0.0))
            market_time = res.get("regularMarketTime")
            
            if market_time:
                thailand_tz = zoneinfo.ZoneInfo("Asia/Bangkok")
                dt_object = datetime.fromtimestamp(market_time, tz=thailand_tz)
                formatted_date = dt_object.strftime("%Y-%m-%d %H:%M:%S")
            else:
                formatted_date = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")

            _vix_cache["value"] = price
            _vix_cache["time_str"] = formatted_date
            _vix_cache["expires"] = time.time() + 60
            return [price, formatted_date]
            
    except Exception as e:
        logging.error(f"Error fetching VIX indicator: {e}")
        
    return [0.0, "N/A"]


def get_world_pe_ratio():
    """
    Fetches comprehensive World P/E and Trend data from worldperatio.com.
    Returns a dict with pe, status, pe_10y, pe_20y, trend_long, trend_short.
    """
    global _pe_cache

    if _pe_cache["data"] is not None and time.time() < _pe_cache["expires"]:
        return _pe_cache["data"], _pe_cache["timestamp"]

    url = "https://worldperatio.com/area/all-world/"
    try:
        from bs4 import BeautifulSoup
        import re
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = {
                "pe": 0.0,
                "status": "Unknown",
                "pe_10y": 0.0,
                "pe_20y": 0.0,
                "trend_long": "N/A",
                "trend_short": "N/A"
            }
            
            full_text = soup.get_text()
            pe_match = re.search(r"All World Stocks is ([\d\.]+)", full_text)
            if pe_match:
                data["pe"] = float(pe_match.group(1))
            
            font_tag = soup.find('font', class_=lambda x: x and x.startswith('pe-'))
            if font_tag:
                data["status"] = font_tag.text.strip()
            
            for b_tag in soup.find_all('b'):
                if "Last 10Y" in b_tag.text:
                    td = b_tag.find_parent('td')
                    if td:
                        next_td = td.find_next_sibling('td')
                        if next_td:
                            data["pe_10y"] = float(next_td.text.strip())
                elif "Last 20Y" in b_tag.text:
                    td = b_tag.find_parent('td')
                    if td:
                        next_td = td.find_next_sibling('td')
                        if next_td:
                            data["pe_20y"] = float(next_td.text.strip())
            
            for b_tag in soup.find_all('b'):
                if "Long Term" in b_tag.text:
                    row = b_tag.find_parent('tr')
                    if row:
                        tds = row.find_all('td')
                        if len(tds) >= 4:
                            data["trend_long"] = tds[3].text.strip()
                elif "Short Term" in b_tag.text:
                    row = b_tag.find_parent('tr')
                    if row:
                        tds = row.find_all('td')
                        if len(tds) >= 4:
                            data["trend_short"] = tds[3].text.strip()

            if data["pe"] > 0:
                _pe_cache["data"] = data
                _pe_cache["timestamp"] = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
                _pe_cache["expires"] = time.time() + _CACHE_TTL
                return _pe_cache["data"], _pe_cache["timestamp"]
                
    except Exception as e:
        logging.error(f"Error fetching comprehensive World P/E: {e}")
        
    return None, None


def get_all_countries_pe():
    """
    Fetches the P/E ratios for all countries from the worldperatio.com homepage.
    Returns a list of dicts.
    """
    global _countries_cache

    if _countries_cache["data"] is not None and time.time() < _countries_cache["expires"]:
        return _countries_cache["data"], _countries_cache["timestamp"]

    url = "https://worldperatio.com/"
    try:
        from bs4 import BeautifulSoup
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if not table:
                return None, None

            results = []
            rows = table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) < 10: # Data rows have many cells
                    continue
                
                # td[1] = Code, td[2] = Name, td[3] = PE, td[4] = Status, td[13] = Trend
                country_name = tds[2].text.strip()
                if not country_name:
                    continue
                
                try:
                    pe_text = tds[3].text.strip()
                    if not pe_text: continue
                    pe_ratio = float(pe_text)
                    
                    status = tds[4].text.strip()
                    
                    # Trend is usually in a cell with w3-text-red or w3-text-teal
                    trend = "N/A"
                    for i in range(10, len(tds)):
                        if "%" in tds[i].text:
                            trend = tds[i].text.strip()
                            break
                    
                    results.append({
                        "country": country_name,
                        "pe": pe_ratio,
                        "status": status,
                        "trend": trend
                    })
                except (ValueError, IndexError):
                    continue

            if results:
                _countries_cache["data"] = results
                _countries_cache["timestamp"] = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
                _countries_cache["expires"] = time.time() + _CACHE_TTL
                return _countries_cache["data"], _countries_cache["timestamp"]
                
    except Exception as e:
        logging.error(f"Error fetching all countries P/E: {e}")
    
    return None, None

def get_fear_and_greed_index():
    """
    Fetches the Crypto Fear & Greed Index.
    Returns [value (0-100), status_string, timestamp]
    """
    global _fng_cache
    if _fng_cache["value"] is not None and time.time() < _fng_cache["expires"]:
        return [_fng_cache["value"], _fng_cache["status"], _fng_cache["timestamp"]]

    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data and "data" in data and len(data["data"]) > 0:
            val = int(data["data"][0]["value"])
            status = data["data"][0]["value_classification"]
            _fng_cache["value"] = val
            _fng_cache["status"] = status
            _fng_cache["timestamp"] = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
            _fng_cache["expires"] = time.time() + _CACHE_TTL
            return [val, status, _fng_cache["timestamp"]]
    except Exception as e:
        logging.error(f"Error fetching Fear & Greed Index: {e}")
    
    return [50, "Neutral", None]


def get_usd_thb_rate():
    """
    Fetches the real-time USD/THB exchange rate from Yahoo Finance.
    Returns [rate, timestamp] or [0.0, None] if failed.
    """
    global _thb_cache
    if _thb_cache["value"] is not None and time.time() < _thb_cache["expires"]:
        return _thb_cache["value"], _thb_cache["timestamp"]

    # Source 1: Yahoo Finance (High Real-time Accuracy)
    try:
        # Add random parameter to bypass cache
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/USDTHB=X?interval=1m&range=1d&_={int(time.time())}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data and "chart" in data and data["chart"]["result"]:
            res = data["chart"]["result"][0]["meta"]
            rate = float(res["regularMarketPrice"])
            _thb_cache["value"] = rate
            _thb_cache["timestamp"] = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
            _thb_cache["expires"] = time.time() + 60  # 1 min cache
            return rate, _thb_cache["timestamp"]
    except Exception as e:
        logging.error(f"Yahoo Finance USD/THB error: {e}")

    # Source 2: Fallback (Less real-time, but reliable)
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data and "rates" in data and "THB" in data["rates"]:
            rate = float(data["rates"]["THB"])
            _thb_cache["value"] = rate
            _thb_cache["timestamp"] = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
            _thb_cache["expires"] = time.time() + 300  # 5 min cache for fallback
            return rate, _thb_cache["timestamp"]
    except Exception as e:
        logging.error(f"Fallback USD/THB error: {e}")
    
    return 0.0, None


def get_all_max_pain(currency="BTC"):
    """
    Fetches options data from Deribit and calculates the Max Pain price 
    for all available expiration dates.
    Returns a dictionary: { "DDMMMYY": float_price, ... }
    """
    global _max_pain_cache
    if _max_pain_cache["data"] is not None and time.time() < _max_pain_cache["expires"]:
        return _max_pain_cache["data"], _max_pain_cache["timestamp"]

    try:
        url = f'https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={currency}&kind=option'
        res = requests.get(url, timeout=15).json()
        summaries = res.get('result', [])
        
        expirations = {}
        for s in summaries:
            name = s.get('instrument_name', '')
            parts = name.split('-')
            if len(parts) != 4: continue
            
            _, exp_date_str, strike_str, option_type = parts
            strike = float(strike_str)
            oi = s.get('open_interest', 0)
            
            if exp_date_str not in expirations:
                expirations[exp_date_str] = {'calls': {}, 'puts': {}}
                
            if option_type == 'C':
                expirations[exp_date_str]['calls'][strike] = expirations[exp_date_str]['calls'].get(strike, 0) + oi
            elif option_type == 'P':
                expirations[exp_date_str]['puts'][strike] = expirations[exp_date_str]['puts'].get(strike, 0) + oi

        if not expirations:
            return {}

        def parse_date(d_str):
            try:
                return datetime.strptime(d_str, "%d%b%y")
            except:
                return datetime.max
        
        sorted_exp = sorted(expirations.keys(), key=parse_date)
        results = {}
        
        for exp_date in sorted_exp:
            data = expirations[exp_date]
            calls = data['calls']
            puts = data['puts']
            
            all_strikes = set(calls.keys()) | set(puts.keys())
            if not all_strikes: continue
            all_strikes = sorted(list(all_strikes))
            
            min_loss = float('inf')
            max_pain = 0
            
            for assumed_price in all_strikes:
                total_loss = 0
                for strike, oi in calls.items():
                    if assumed_price > strike:
                        total_loss += (assumed_price - strike) * oi
                for strike, oi in puts.items():
                    if assumed_price < strike:
                        total_loss += (strike - assumed_price) * oi
                        
                if total_loss < min_loss:
                    min_loss = total_loss
                    max_pain = assumed_price
                    
            results[exp_date] = max_pain

        if results:
            _max_pain_cache["data"] = results
            _max_pain_cache["timestamp"] = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
            _max_pain_cache["expires"] = time.time() + _CACHE_TTL
            return results, _max_pain_cache["timestamp"]

    except Exception as e:
        logging.error(f"Error calculating max pain: {e}")

    return {}, None


def get_polymarket_crypto_events(limit: int = 10):
    """
    Fetches the top active crypto events from Polymarket.
    Returns a list of dicts with title, volume, and outcomes/prices.
    """
    global _poly_cache
    if _poly_cache["data"] is not None and time.time() < _poly_cache["expires"]:
        return _poly_cache["data"], _poly_cache["timestamp"]

    try:
        # Use the specific 'Crypto Prices' tag ID (1312) to find these markets directly
        # Fetching a large batch to ensure we catch daily/weekly/monthly variations
        url = f"https://gamma-api.polymarket.com/events?active=true&closed=false&tag_id=1312&limit=200"
        response = requests.get(url, timeout=10)
        events_data = response.json()
        
        now = datetime.now(thailand_tz)
        current_month = now.strftime('%B').lower()
        # Create a few variations of current day to be safe (e.g. 'May 16', 'May 16th', '16 May')
        day_num = now.day
        day_str_1 = f"{now.strftime('%b')} {day_num}" # 'May 16'
        day_str_2 = f"{now.strftime('%B')} {day_num}" # 'May 16'
        
        results = []
        for e in events_data:
            if 'markets' in e and len(e['markets']) > 0:
                title = e.get('title', 'Unknown Event')
                title_lower = title.lower()
                
                # Check if it matches current date or month
                is_current_day = day_str_1.lower() in title_lower or day_str_2.lower() in title_lower
                is_current_month = current_month in title_lower
                
                all_outcomes = []
                for m in e.get('markets', []):
                    # Check outcomes and prices
                    try:
                        outcomes = m.get('outcomes', [])
                        prices = m.get('outcomePrices', [])
                        
                        if isinstance(outcomes, str): outcomes = json.loads(outcomes)
                        if isinstance(prices, str): prices = json.loads(prices)
                    except:
                        outcomes = []
                        prices = []
                    
                    # For price markets, we usually care about the 'Yes' probability
                    # Or the specific name of the outcome if it's not Yes/No
                    for i in range(min(len(outcomes), len(prices))):
                        name = outcomes[i]
                        try:
                            prob = float(prices[i]) * 100
                            # Filter out < 2% as requested
                            if prob < 2.0:
                                continue
                                
                            # If it's a Yes/No market, we often want the Question text as the name
                            if name.lower() == 'yes':
                                market_title = m.get('question', title)
                                # Clean up the title (remove 'Will Bitcoin', 'in May', etc.)
                                market_title = market_title.replace('Will Bitcoin ', '').replace('Will Ethereum ', '')
                                market_title = market_title.replace(' in May?', '').replace('reach ', '').replace('dip to ', 'dip ')
                                all_outcomes.append((market_title, prob))
                            elif name.lower() != 'no':
                                # Multi-outcome market (like "What price...")
                                all_outcomes.append((name, prob))
                        except:
                            pass

                # Only add if we have valid outcomes to show
                if all_outcomes:
                    # Use the volume from the first market as the event volume
                    event_volume = 0.0
                    if e.get('markets'):
                        event_volume = float(e['markets'][0].get('volume', 0.0))

                    results.append({
                        "title": title,
                        "volume": event_volume,
                        "outcomes": all_outcomes,
                        "is_featured": is_current_day or is_current_month
                    })
        
        # Sort by featured status first, then by volume descending
        results.sort(key=lambda x: (x['is_featured'], x['volume']), reverse=True)
        
        # Apply the final limit requested by the user
        results = results[:limit]
        
        if results:
            _poly_cache["data"] = results
            _poly_cache["timestamp"] = datetime.now(thailand_tz).strftime("%Y-%m-%d %H:%M:%S")
            _poly_cache["expires"] = time.time() + 300  # 5 minute cache to keep it very real-time
            return results, _poly_cache["timestamp"]
            
    except Exception as e:
        logging.error(f"Error fetching Polymarket data: {e}")
        
    return [], None
