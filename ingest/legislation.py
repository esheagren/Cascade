import os
import pandas as pd
import re
import httpx
import time
from datetime import datetime, timedelta
from dagster import asset

from settings import DATA_DIR

def fetch_new_bills() -> int:
    """
    Wrapper for Congress.gov API to count documents with AI-related terms
    """
    # Base URL for the Congress.gov API
    base_url = "https://api.congress.gov/v3/bill"
    
    # Get bills from the last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Format dates for API
    from_date = start_date.strftime("%Y-%m-%d")
    to_date = end_date.strftime("%Y-%m-%d")
    
    # Set up parameters
    params = {
        "fromDateTime": f"{from_date}T00:00:00Z",
        "toDateTime": f"{to_date}T23:59:59Z",
        "limit": 250,  # Maximum allowed
        "format": "json",
        # Add your API key here if required
        # "api_key": os.getenv("CONGRESS_API_KEY")
    }
    
    # Make request
    response = httpx.get(base_url, params=params)
    response.raise_for_status()
    data = response.json()
    
    # Count bills with AGI or frontier AI mentions
    count = 0
    bills_with_terms = []
    pattern = r'\bAGI\b|\bfrontier AI\b|\bartificial general intelligence\b'
    
    # Check each bill's text
    for bill in data.get('bills', []):
        bill_id = bill.get('billNumber')
        bill_type = bill.get('billType')
        
        # Get bill text
        text_url = f"{base_url}/{bill_type}/{bill_id}/text"
        try:
            text_response = httpx.get(text_url)
            text_response.raise_for_status()
            bill_text = text_response.text
            
            # Check for pattern
            if re.search(pattern, bill_text, re.IGNORECASE):
                count += 1
                bills_with_terms.append({
                    'bill_id': bill_id,
                    'bill_type': bill_type,
                    'date': bill.get('latestAction', {}).get('actionDate', '')
                })
            
            # Respect rate limits
            time.sleep(0.1)
        except Exception as e:
            print(f"Error getting text for bill {bill_type} {bill_id}: {e}")
    
    # Save the bills with terms
    if bills_with_terms:
        df = pd.DataFrame(bills_with_terms)
        df['date'] = datetime.now().strftime('%Y-%m-%d')
        
        # Save to staging
        staging_dir = DATA_DIR / "staging" / "legislation"
        os.makedirs(staging_dir, exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        parquet_path = staging_dir / f"{today}.parquet"
        df.to_parquet(parquet_path)
    
    return count

@asset
def legislation_asset():
    """
    Dagster asset to fetch Congress.gov data and write to staging Parquet
    """
    count = fetch_new_bills()
    
    # Create DataFrame with count
    df = pd.DataFrame([{
        'date': datetime.now().strftime('%Y-%m-%d'),
        'ai_bill_count': count
    }])
    
    # Save to staging
    staging_dir = DATA_DIR / "staging" / "legislation"
    os.makedirs(staging_dir, exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    parquet_path = staging_dir / f"{today}.parquet"
    df.to_parquet(parquet_path)
    
    return df
