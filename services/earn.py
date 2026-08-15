import os
import time
import hmac
import hashlib
import requests
import logging
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

logger = logging.getLogger(__name__)

def signed_request(path: str, params: dict = None) -> Tuple[Dict[str, Any], int]:
    if params is None:
        params = {}
    if not api_key or not api_secret:
        return {}, 401

    params['timestamp'] = int(time.time() * 1000)
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    
    url = f"https://api.binance.com{path}?{query_string}&signature={signature}"
    headers = {'X-MBX-APIKEY': api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json(), response.status_code
    except Exception as e:
        logger.error(f"Error fetching {path}: {e}")
        return {}, 500

def get_dual_investment_positions(status: str = 'SETTLED', limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetches dual investment positions.
    Status can be 'SETTLED', 'PURCHASE_SUCCESS', etc.
    """
    res, code = signed_request('/sapi/v1/dci/product/positions', {
        'status': status,
        'pageSize': limit
    })
    
    if code == 200:
        return res.get('list', [])
    else:
        logger.error(f"Failed to fetch dual investment positions: {code} - {res}")
        return []

def get_dual_investment_products(option_type: str, invest_coin: str, exercised_coin: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetches available Dual Investment products for subscription.
    option_type: 'CALL' (Sell High) or 'PUT' (Buy Low)
    invest_coin: e.g. 'BTC' for CALL, 'USDT' for PUT
    exercised_coin: e.g. 'USDT' for CALL, 'BTC' for PUT
    """
    res, code = signed_request('/sapi/v1/dci/product/list', {
        'optionType': option_type.upper(),
        'investCoin': invest_coin.upper(),
        'exercisedCoin': exercised_coin.upper(),
        'pageSize': limit
    })
    
    if code == 200:
        return res.get('list', [])
    else:
        logger.error(f"Failed to fetch dual investment products ({option_type} {invest_coin}->{exercised_coin}): {code} - {res}")
        return []

def scan_dual_investment_targets() -> List[Dict[str, Any]]:
    """
    Scans Binance Dual Investment product list against all saved target rules.
    """
    from core.database import get_dual_targets
    targets = get_dual_targets()
    if not targets:
        return []

    results = []
    product_cache: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}

    for target in targets:
        coin = target['coin'].upper()
        strike_target = float(target['strike_price'])
        min_apr = float(target['min_apr'])
        opt_type_raw = target['option_type'].upper().replace("_", "").replace("-", "")

        # BUYLOW / PUT: invest USDT, exercise COIN (PUT)
        # SELLHIGH / CALL: invest COIN, exercise USDT (CALL)
        if opt_type_raw in ("BUYLOW", "PUT", "BUY"):
            binance_opt = "PUT"
            invest_c = "USDT"
            exercise_c = coin
        elif opt_type_raw in ("SELLHIGH", "CALL", "SELL"):
            binance_opt = "CALL"
            invest_c = coin
            exercise_c = "USDT"
        else:
            continue

        cache_key = (binance_opt, invest_c, exercise_c)
        if cache_key not in product_cache:
            product_cache[cache_key] = get_dual_investment_products(binance_opt, invest_c, exercise_c)

        products = product_cache[cache_key]
        for p in products:
            if not p.get('canPurchase', True):
                continue

            try:
                p_strike = float(p.get('strikePrice', 0))
                raw_apr = float(p.get('apr', 0))
                p_apr = raw_apr * 100 if raw_apr < 1.0 else raw_apr
            except (ValueError, TypeError):
                continue

            if abs(p_strike - strike_target) < 0.5 or (strike_target > 0 and abs(p_strike - strike_target) / strike_target < 0.001):
                if p_apr >= min_apr:
                    results.append({
                        "target": target,
                        "product": p,
                        "apr": p_apr,
                        "strike": p_strike
                    })

    return results

