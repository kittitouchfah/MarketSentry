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
