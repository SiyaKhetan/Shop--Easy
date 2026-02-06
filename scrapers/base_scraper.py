"""
Base scraper class for all e-commerce platforms
"""
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Optional
import time


class BaseScraper(ABC):
    """Base class for all e-commerce scrapers"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--window-size=1920,1080')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            if not self.headless:
                self.driver.maximize_window()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Chrome WebDriver: {str(e)}. Make sure Chrome browser is installed.")
    
    @abstractmethod
    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        """
        Search for a product and return list of results
        
        Args:
            product_name: Name of the product to search
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing product information
            Each dict should have: title, price, url, platform, rating (optional)
        """
        pass
    
    def extract_price(self, price_text: str) -> float:
        """Extract numeric price from text"""
        import re
        if not price_text:
            return 0.0
        # Remove currency symbols, commas, and extract numbers with decimal
        # Handle formats like "₹1,234.56", "$1234.56", "1,234", etc.
        price_str = re.sub(r'[^\d.]', '', str(price_text))
        # Remove multiple dots, keep only the last one (for decimal)
        if price_str.count('.') > 1:
            parts = price_str.split('.')
            price_str = ''.join(parts[:-1]) + '.' + parts[-1]
        try:
            price = float(price_str)
            return price if price > 0 else 0.0
        except (ValueError, AttributeError):
            return 0.0
    
    def wait_for_element(self, by: By, value: str, timeout: int = None):
        """Wait for element to be present"""
        wait_time = timeout or self.timeout
        return WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located((by, value))
        )
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
