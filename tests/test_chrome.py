import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

service = Service(os.getenv("CHROME_DRIVER_PATH", "chromedriver"))
driver  = webdriver.Chrome(service=service)

driver.get("https://example.com")
print(driver.title)  # should print “Example Domain”
driver.quit()