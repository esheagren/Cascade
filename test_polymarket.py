#!/usr/bin/env python3
"""
Test script for validating Polymarket API connection
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
POLY_API = os.getenv("POLY_API")

if not POLY_API:
    print("Error: POLY_API environment variable not found.")
    sys.exit(1)

print(f"Found API key: {POLY_API[:5]}...{POLY_API[-4:]}")

# Try py-clob-client first
try:
    from py_clob_client.client import ClobClient
    
    print("\nTesting connection with py-clob-client...")
    client = ClobClient(key=POLY_API, chain_id=137)  # 137 is for Polygon network
    
    # Example contract ID (one from your codebase)
    contract_id = "0x4c5435b2be38fae3dcecfe1e2bf04bbb2326b906"
    
    # Get market data
    print(f"Fetching market data for contract: {contract_id}")
    market_data = client.get_market(market_id=contract_id)
    
    if market_data:
        print("Successfully fetched market data:")
        print(f"  Market name: {market_data.get('name', 'Unknown')}")
        print(f"  Mid price: {market_data.get('midPrice', 'N/A')}")
        print(f"  Volume: {market_data.get('volume', 'N/A')}")
    else:
        print("No market data returned.")
    
except ImportError:
    print("py-clob-client not available.")
except Exception as e:
    print(f"Error using ClobClient: {e}")

# Also try to import polymarket-py as a fallback
try:
    from polymarket.api import PolymarketAPI
    
    print("\nTesting connection with polymarket-py...")
    api = PolymarketAPI(api_key=POLY_API)
    
    # Example contract ID (one from your codebase)
    contract_id = "0x4c5435b2be38fae3dcecfe1e2bf04bbb2326b906"
    
    # Get market data
    print(f"Fetching market data for contract: {contract_id}")
    market_data = api.get_market(market_id=contract_id)
    
    if market_data:
        print("Successfully fetched market data:")
        print(f"  Market name: {market_data.get('name', 'Unknown')}")
        print(f"  Mid price: {market_data.get('midPrice', 'N/A')}")
        print(f"  Volume: {market_data.get('volume', 'N/A')}")
    else:
        print("No market data returned.")
        
except ImportError:
    print("polymarket-py not available.")
except Exception as e:
    print(f"Error using PolymarketAPI: {e}")

print("\nTest completed.") 