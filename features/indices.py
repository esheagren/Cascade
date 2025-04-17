import os
import pandas as pd
import numpy as np
import duckdb
from datetime import datetime, timedelta
from dagster import asset, DependsOn

from settings import DATA_DIR
from ingest.google_trends import fetch_trends
from ingest.polymarket import polymarket_asset
from ingest.capability_scraper import capability_asset
from ingest.legislation import legislation_asset
from ingest.news_pixels import news_pixels_asset

def normalize_data(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Normalize data to z-scores
    """
    result = df.copy()
    for column in columns:
        if column in result.columns:
            mean = result[column].mean()
            std = result[column].std()
            if std > 0:
                result[column] = (result[column] - mean) / std
            else:
                result[column] = 0  # Handle case where std is 0
    return result

@asset(deps=[
    fetch_trends,
    polymarket_asset,
    capability_asset,
    legislation_asset,
    news_pixels_asset
])
def daily_index():
    """
    Dagster asset that depends on all ingest assets.
    Reads latest Parquets, normalises to z-scores, outputs a DuckDB table.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Connect to DuckDB
    db_path = DATA_DIR / "agidash.duckdb"
    con = duckdb.connect(str(db_path))
    
    # Create tables if they don't exist
    con.execute("""
        CREATE TABLE IF NOT EXISTS daily_index (
            date DATE,
            capability FLOAT,
            attention FLOAT,
            market FLOAT,
            regulatory FLOAT
        )
    """)
    
    # 1. Capability Index (from capability_scraper)
    capability_path = DATA_DIR / "staging" / "capabilities" / f"{today}.parquet"
    if capability_path.exists():
        capabilities_df = pd.read_parquet(capability_path)
        # Average the scores across models and metrics
        capability_score = capabilities_df.filter(regex='MMMU|MMLU-pro|GSM-Hard').mean().mean()
    else:
        capability_score = 0
    
    # 2. Attention Index (from google_trends and news_pixels)
    # Google Trends
    trends_path = DATA_DIR / "staging" / "google_trends" / f"{today}.parquet"
    if trends_path.exists():
        trends_df = pd.read_parquet(trends_path)
        trends_score = trends_df.mean().mean()
    else:
        trends_score = 0
    
    # News Pixels
    news_path = DATA_DIR / "staging" / "news_pixels" / f"{today}.parquet"
    if news_path.exists():
        news_df = pd.read_parquet(news_path)
        news_score = news_df['ai_pixel_percentage'].mean()
    else:
        news_score = 0
    
    # Combine for attention index
    attention_score = (trends_score + news_score) / 2
    
    # 3. Market Index (from polymarket)
    market_path = DATA_DIR / "staging" / "polymarket" / f"{today}.parquet"
    if market_path.exists():
        market_df = pd.read_parquet(market_path)
        market_score = market_df['price'].mean()
    else:
        market_score = 0
    
    # 4. Regulatory Index (from legislation)
    regulatory_path = DATA_DIR / "staging" / "legislation" / f"{today}.parquet"
    if regulatory_path.exists():
        regulatory_df = pd.read_parquet(regulatory_path)
        regulatory_score = regulatory_df['ai_bill_count'].mean()
    else:
        regulatory_score = 0
    
    # Create the daily index DataFrame
    index_df = pd.DataFrame([{
        'date': today,
        'capability': capability_score,
        'attention': attention_score,
        'market': market_score,
        'regulatory': regulatory_score
    }])
    
    # Normalize the indices
    # First, get historical data
    historical_df = pd.DataFrame(con.execute("""
        SELECT * FROM daily_index
        ORDER BY date DESC
        LIMIT 180
    """).fetchall())
    
    if not historical_df.empty:
        historical_df.columns = ['date', 'capability', 'attention', 'market', 'regulatory']
        # Combine with today's data
        combined_df = pd.concat([historical_df, index_df])
        # Normalize
        columns_to_normalize = ['capability', 'attention', 'market', 'regulatory']
        normalized_df = normalize_data(combined_df, columns_to_normalize)
        # Get just today's normalized data
        index_df = normalized_df[normalized_df['date'] == today]
    
    # Insert into DuckDB
    con.execute("""
        INSERT INTO daily_index
        VALUES (?, ?, ?, ?, ?)
    """, [
        today,
        float(index_df['capability'].iloc[0]),
        float(index_df['attention'].iloc[0]),
        float(index_df['market'].iloc[0]),
        float(index_df['regulatory'].iloc[0])
    ])
    
    con.close()
    
    return index_df
