import pandas as pd
from pytrends.request import TrendReq
from dagster import asset
from datetime import datetime
import os

from settings import DATA_DIR

@asset
def fetch_trends(keywords: list[str] = ["artificial intelligence", "AGI"], geo="US") -> pd.DataFrame:
    """
    Fetches Google Trends data for a list of keywords
    """
    pytrends = TrendReq(hl='en-US', tz=360)
    pytrends.build_payload(keywords, cat=0, timeframe='now 7-d', geo=geo)
    interest_over_time_df = pytrends.interest_over_time()
    
    # Remove the isPartial column
    if 'isPartial' in interest_over_time_df.columns:
        interest_over_time_df = interest_over_time_df.drop('isPartial', axis=1)
    
    # Create output directory if it doesn't exist
    raw_dir = DATA_DIR / "raw" / "google"
    os.makedirs(raw_dir, exist_ok=True)
    
    # Save to CSV
    today = datetime.now().strftime("%Y-%m-%d")
    csv_path = raw_dir / f"{today}.csv"
    interest_over_time_df.to_csv(csv_path)
    
    # Save to Parquet for the pipeline
    staging_dir = DATA_DIR / "staging" / "google_trends"
    os.makedirs(staging_dir, exist_ok=True)
    parquet_path = staging_dir / f"{today}.parquet"
    interest_over_time_df.to_parquet(parquet_path)
    
    return interest_over_time_df
