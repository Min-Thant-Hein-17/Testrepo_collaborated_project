import pandas as pd
from datetime import datetime, timedelta, timezone
from stellar_sdk import Server
from decimal import Decimal, getcontext
import requests  # Required for the API call

# Fixed-point precision for blockchain math
getcontext().prec = 28 

def get_account_name(account_id, cache_dict):
    """
    Checks the cache for the account_id. 
    If not found, calls the Federation API and caches the result.
    """
    if not account_id or len(account_id) < 16:
        return account_id

    # 1. If we already looked up this account, return the saved name instantly
    if account_id in cache_dict:
        return cache_dict[account_id]

    # 2. If not in cache, call the Federation API (Reverse Lookup: type=id)
    # Replace the base URL if NUGpay uses a specific custom endpoint
    url = f"https://federation.nugpay.app/federation?q={account_id}&type=id"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            stellar_address = data.get("stellar_address", "")
            
            # 3. Extract the username before "*nugpay.app"
            if stellar_address and "*nugpay.app" in stellar_address:
                username = stellar_address.split("*")[0]
                
                # Save to dictionary and return
                cache_dict[account_id] = username
                return username
                
    except requests.exceptions.RequestException as e:
        print(f"API Error for {account_id}: {e}")

    # 4. Fallback: If API fails or account has no federation name, mask the ID
    fallback_name = f"{account_id[:8]}***{account_id[-4:]}"
    cache_dict[account_id] = fallback_name
    return fallback_name


def analyze_stellar_account(account_id, months=1):
    server = Server("https://horizon.stellar.org")
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(days=30 * months)
    
    processed_data = []
    
    # Initialize the empty dictionary to hold our API results
    name_cache = {} 
    
    try:
        payments_call = server.payments().for_account(account_id).order(desc=True).limit(200)
        records = payments_call.call()

        while records['_embedded']['records']:
            for record in records['_embedded']['records']:
                dt = datetime.strptime(record['created_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                
                if dt < start_date:
                    records['_embedded']['records'] = []
                    break
                
                asset_code = record.get('asset_code')
                if asset_code not in ["DMMK", "nUSDT"]:
                    continue

                raw_val = Decimal(record.get('amount', '0'))
                final_val = raw_val * Decimal('1000') if asset_code == "DMMK" else raw_val
                is_sender = record.get('from') == account_id
                
                # Get the raw ID of the other party
                raw_other_account = record.get('to') if is_sender else record.get('from')
                
                # Resolve the name using our dictionary cache
                display_name = get_account_name(raw_other_account, name_cache)
                
                processed_data.append({
                    "timestamp": dt,
                    "date": dt.date(),
                    "month_name": dt.strftime("%B"),
                    "week_num": f"Week {dt.isocalendar()[1]}",
                    "direction": "OUTGOING" if is_sender else "INCOMING",
                    "other_account": display_name,  # Now stores "meepwar" instead of "GCPGE..."
                    "amount": float(final_val),
                    "asset": asset_code
                })
            
            records = payments_call.next()
            if not records['_embedded']['records']: break

        return processed_data
    except Exception as e:
        print(f"Error: {e}")
        return None
