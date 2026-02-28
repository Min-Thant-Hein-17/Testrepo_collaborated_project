import json
import pandas as pd
from datetime import datetime, timedelta, timezone
from stellar_sdk import Server

def analyze_stellar_account(account_id, months=1):
    """
    Fetches Stellar transaction data, performs feature engineering for ML,
    and returns a structured dictionary for dashboard/analysis use.
    """
    # 1. Setup Connection
    server = Server("https://horizon.stellar.org")
    # Use timezone-aware UTC to prevent comparison errors
    start_date = datetime.now(timezone.utc) - timedelta(days=30 * months)
    
    processed_data = []
    total_in = 0.0
    total_out = 0.0
    
    try:
        # 2. Fetch Payments with Pagination
        payments_call = server.payments().for_account(account_id).order(desc=True).limit(200)
        records = payments_call.call()

        while records['_embedded']['records']:
            for record in records['_embedded']['records']:
                # Parse created_at to a UTC datetime object
                dt = datetime.strptime(record['created_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                
                # Stop if we hit transactions older than our timeframe
                if dt < start_date:
                    records['_embedded']['records'] = [] 
                    break
                
                # Basic Extraction
                amount = float(record.get('amount', record.get('starting_balance', 0)))
                is_sender = record.get('from') == account_id
                
                # Identify Counterparty & Direction
                counterparty = record.get('to') if is_sender else (record.get('from') or record.get('funder'))
                direction = "OUTGOING" if is_sender else "INCOMING"
                
                if is_sender: 
                    total_out += amount
                else: 
                    total_in += amount

                # Append record with ML-friendly features (hour, day of week)
                processed_data.append({
                    "timestamp": record['created_at'],
                    "hour": dt.hour,
                    "day_of_week": dt.weekday(), # 0=Monday, 6=Sunday
                    "tx_hash": record['transaction_hash'],
                    "type": record['type'],
                    "direction": direction,
                    "counterparty": counterparty,
                    "amount": amount,
                    "asset": record.get('asset_code', 'XLM')
                })
            
            # Navigate to the next page of results
            records = payments_call.next()
            if not records['_embedded']['records']: 
                break

    except Exception as e:
        print(f"Error fetching data from Horizon: {e}")
        return None

    if not processed_data:
        return None

    # 3. Aggregate Analysis (Feature Engineering)
    df = pd.DataFrame(processed_data)
    
    # Calculate key metrics for ML Model inputs
    analysis_package = {
        "account_metadata": {
            "account_id": account_id,
            "total_in": round(total_in, 2),
            "total_out": round(total_out, 2),
            "net_flow": round(total_in - total_out, 2),
            "tx_frequency": len(df),
            "unique_counterparties": df['counterparty'].nunique(),
            "avg_tx_size": round(df['amount'].mean(), 2)
        },
        "raw_transactions": processed_data
    }

    return analysis_package
    