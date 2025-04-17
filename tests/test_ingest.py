import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import vcr

from ingest.google_trends import fetch_trends
from ingest.polymarket import fetch_contract
from ingest.capability_scraper import fetch_capabilities
from ingest.legislation import fetch_new_bills
from ingest.news_pixels import analyze_image
import numpy as np

# Configure VCR for recording HTTP interactions
my_vcr = vcr.VCR(
    cassette_library_dir='tests/fixtures/vcr_cassettes',
    record_mode='once',
    match_on=['uri', 'method'],
)

# Mock settings for tests
@pytest.fixture(autouse=True)
def mock_settings(monkeypatch, tmp_path):
    """Mock settings for tests"""
    # Create temp data directory
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    
    # Mock DATA_DIR
    monkeypatch.setattr("ingest.google_trends.DATA_DIR", data_dir)
    monkeypatch.setattr("ingest.polymarket.DATA_DIR", data_dir)
    monkeypatch.setattr("ingest.capability_scraper.DATA_DIR", data_dir)
    monkeypatch.setattr("ingest.legislation.DATA_DIR", data_dir)
    monkeypatch.setattr("ingest.news_pixels.DATA_DIR", data_dir)
    
    # Mock API keys
    monkeypatch.setattr("ingest.polymarket.POLY_API", "fake_api_key")


@my_vcr.use_cassette('google_trends.yaml')
def test_fetch_trends():
    """Test the Google Trends fetcher"""
    keywords = ["AI", "artificial intelligence"]
    df = fetch_trends(keywords, geo="US")
    
    # Basic validation
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    
    # Check if keywords are in columns
    for keyword in keywords:
        assert any(keyword.lower() in col.lower() for col in df.columns)


@patch('ingest.polymarket.PolymarketAPI')
def test_fetch_contract(mock_polymarket):
    """Test the Polymarket contract fetcher"""
    # Mock the API response
    mock_api_instance = mock_polymarket.return_value
    mock_api_instance.get_market.return_value = {'midPrice': '0.75'}
    
    # Call the function
    price = fetch_contract("test_contract_id")
    
    # Assertions
    assert mock_api_instance.get_market.called
    assert mock_api_instance.get_market.call_args[1]['market_id'] == "test_contract_id"
    assert price == 0.75


@my_vcr.use_cassette('capability_scraper.yaml')
@pytest.mark.asyncio
async def test_fetch_capabilities():
    """Test the capability scraper"""
    capabilities = await fetch_capabilities()
    
    # Basic validation
    assert isinstance(capabilities, dict)
    assert len(capabilities) > 0
    
    # Check for expected metrics in at least one model
    metrics_found = False
    for model_data in capabilities.values():
        metrics = set(model_data.keys())
        if any(metric in metrics for metric in ['MMMU', 'MMLU-pro', 'GSM-Hard']):
            metrics_found = True
            break
    
    assert metrics_found, "No expected metrics found in any model"


@my_vcr.use_cassette('legislation.yaml')
def test_fetch_new_bills():
    """Test the legislation fetcher"""
    with patch('ingest.legislation.httpx.get') as mock_get:
        # Mock the API response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'bills': [
                {
                    'billNumber': '123',
                    'billType': 'hr',
                    'latestAction': {'actionDate': '2023-05-01'}
                }
            ]
        }
        mock_response.text = "This bill concerns AGI regulation"
        mock_get.return_value = mock_response
        
        # Call the function
        count = fetch_new_bills()
        
        # Assertions
        assert mock_get.called
        assert count == 1


def test_analyze_image():
    """Test the image analysis function"""
    # Create a simple test image with some text
    # This would be a 100x100 white image
    image = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    with patch('ingest.news_pixels.pytesseract.image_to_string') as mock_ocr_string:
        with patch('ingest.news_pixels.pytesseract.image_to_data') as mock_ocr_data:
            # Mock OCR text result
            mock_ocr_string.return_value = "This is a test with AI mentioned"
            
            # Mock OCR data result
            mock_ocr_data.return_value = {
                'text': ['This', 'is', 'a', 'test', 'with', 'AI', 'mentioned'],
                'left': [10, 30, 50, 70, 10, 30, 50],
                'top': [10, 10, 10, 10, 30, 30, 30],
                'width': [20, 20, 20, 20, 20, 20, 20],
                'height': [20, 20, 20, 20, 20, 20, 20]
            }
            
            # Call the function
            percentage = analyze_image(image)
            
            # Assertions
            assert mock_ocr_string.called
            assert mock_ocr_data.called
            assert percentage >= 0
