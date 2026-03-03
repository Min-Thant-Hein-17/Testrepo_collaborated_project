import pandas as pd
from datetime import datetime, timedelta, timezone
from stellar_sdk import Server
from decimal import Decimal, getcontext

# Fixed-point precision for blockchain math
getcontext().prec = 28 

def mask_account(account_id):
    """GABC1234*******WXYZ5678"""
    if not account_id or len(account_id) < 16:
        return account_id
    return f"{account_id[:8]}*******{account_id[-8:]}"

def analyze_stellar_account(account_id, months=1):
    server = Server("https://horizon.stellar.org")
    # Correct way to get current UTC time
    now_utc = datetime.now(timezone.utc)
    start_date = now_utc - timedelta(days=30 * months)
    
    processed_data = []
    
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
                # Ignore XLM and other assets
                if asset_code not in ["DMMK", "nUSDT"]:
                    continue

                raw_val = Decimal(record.get('amount', '0'))
                
                # Logic: DMMK x 1000, nUSDT stays raw
                final_val = raw_val * Decimal('1000') if asset_code == "DMMK" else raw_val

                is_sender = record.get('from') == account_id
                
                processed_data.append({
                    "timestamp": dt,
                    "date": dt.date(),
                    "month_name": dt.strftime("%B"),
                    "week_num": f"Week {dt.isocalendar()[1]}",
                    "direction": "OUTGOING" if is_sender else "INCOMING",
                    "other_account": mask_account(record.get('to') if is_sender else record.get('from')),
                    "amount": float(final_val), # Convert to float for Plotly
                    "asset": asset_code
                })
            
            records = payments_call.next()
            if not records['_embedded']['records']: break

        return processed_data
    except Exception as e:
        print(f"Error: {e}")
        return None