import os
import pandas as pd
import numpy as np
import cv2
import pytesseract
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from PIL import Image
import io
from dagster import asset

from settings import DATA_DIR

def take_screenshot(url: str) -> np.ndarray:
    """
    Use Selenium with headless Chrome to take a screenshot of a website
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    
    # Wait for page to load (adjust as needed)
    driver.implicitly_wait(10)
    
    # Take screenshot
    screenshot = driver.get_screenshot_as_png()
    driver.quit()
    
    # Convert to numpy array
    image = Image.open(io.BytesIO(screenshot))
    return np.array(image)

def analyze_image(image: np.ndarray) -> float:
    """
    Use OCR to detect text and calculate percentage of pixels with AI-related terms
    """
    # Convert to grayscale for OCR
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Extract text using OCR
    text = pytesseract.image_to_string(gray)
    
    # Count AI-related terms
    ai_keywords = ["AI", "artificial intelligence", "AGI", "machine learning"]
    
    # Count occurrences
    ai_mentions = sum(keyword.lower() in text.lower() for keyword in ai_keywords)
    
    # Map detected words to image regions
    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    
    # Calculate total pixels
    total_pixels = image.shape[0] * image.shape[1]
    ai_pixels = 0
    
    # For each detected word, check if it contains AI keywords
    for i in range(len(data['text'])):
        word = data['text'][i].lower()
        if any(keyword.lower() in word for keyword in ai_keywords):
            # Calculate area of this word's bounding box
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            ai_pixels += w * h
    
    # Calculate percentage
    percentage = (ai_pixels / total_pixels) * 100 if total_pixels > 0 else 0
    
    return percentage

@asset
def news_pixels_asset():
    """
    Dagster asset to screenshot news sites and analyze AI mentions
    """
    # News sites to analyze
    news_sites = {
        "nyt": "https://www.nytimes.com/",
        "wsj": "https://www.wsj.com/",
        "bbc": "https://www.bbc.com/"
    }
    
    results = {}
    screenshots_dir = DATA_DIR / "raw" / "screenshots"
    os.makedirs(screenshots_dir, exist_ok=True)
    
    for name, url in news_sites.items():
        try:
            # Take screenshot
            image = take_screenshot(url)
            
            # Save screenshot
            today = datetime.now().strftime("%Y-%m-%d")
            img_path = screenshots_dir / f"{name}_{today}.png"
            cv2.imwrite(str(img_path), image)
            
            # Analyze image
            percentage = analyze_image(image)
            results[name] = percentage
        except Exception as e:
            print(f"Error processing {name}: {e}")
            results[name] = 0.0
    
    # Create DataFrame
    df = pd.DataFrame(list(results.items()), columns=['site', 'ai_pixel_percentage'])
    df['date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Save to staging
    staging_dir = DATA_DIR / "staging" / "news_pixels"
    os.makedirs(staging_dir, exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    parquet_path = staging_dir / f"{today}.parquet"
    df.to_parquet(parquet_path)
    
    return df
