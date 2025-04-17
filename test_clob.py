#!/usr/bin/env python3
"""
Simple test script for py-clob-client
"""
from py_clob_client.client import ClobClient

# Use the API key directly from the environment file
api_key = "gWCB1Cac7hvLltxTjZu8QazG_j9HYTLS"
host = "https://clob.polymarket.com"  # Default host for Polymarket API
print(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
print(f"Using host: {host}")

try:
    # Initialize client
    client = ClobClient(host=host, key=api_key, chain_id=137)  # 137 is for Polygon network
    
    # Example contract ID
    contract_id = "0x4c5435b2be38fae3dcecfe1e2bf04bbb2326b906"
    
    print(f"Fetching market data for contract: {contract_id}")
    market_data = client.get_market(market_id=contract_id)
    
    if market_data:
        print("Success! Market data received.")
        print(f"  Market name: {market_data.get('name', 'Unknown')}")
        print(f"  Mid price: {market_data.get('midPrice', 'N/A')}")
    else:
        print("No market data returned.")
        
except Exception as e:
    print(f"Error: {e}")

print("Test completed.") 