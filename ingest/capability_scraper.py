import os
import pandas as pd
import httpx
import yaml
from datetime import datetime
import asyncio
from dagster import asset

from settings import DATA_DIR

async def fetch_capabilities() -> dict:
    """
    Async scraper to fetch latest AI model capabilities from LMSys leaderboard
    """
    url = "https://raw.githubusercontent.com/lmsys/leaderboard/main/leaderboard.yaml"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        
        data = yaml.safe_load(response.text)
        
        # Extract the key metrics: MMMU, MMLU-pro, GSM-Hard
        results = {}
        for model in data.get('models', []):
            model_name = model.get('name')
            metrics = {}
            
            for metric in model.get('metrics', []):
                metric_name = metric.get('name')
                if metric_name in ['MMMU', 'MMLU-pro', 'GSM-Hard']:
                    metrics[metric_name] = metric.get('value')
            
            if metrics:  # Only add models that have at least one of our target metrics
                results[model_name] = metrics
    
    return results

@asset
def capability_asset():
    """
    Dagster asset to fetch AI capability scores and write to staging Parquet
    """
    # Run the async function to get capabilities
    capabilities = asyncio.run(fetch_capabilities())
    
    # Convert to DataFrame
    records = []
    for model, metrics in capabilities.items():
        record = {'model': model}
        record.update(metrics)
        records.append(record)
    
    df = pd.DataFrame(records)
    df['date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Save to staging
    staging_dir = DATA_DIR / "staging" / "capabilities"
    os.makedirs(staging_dir, exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    parquet_path = staging_dir / f"{today}.parquet"
    df.to_parquet(parquet_path)
    
    return df
