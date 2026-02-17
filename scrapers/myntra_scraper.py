"""
Myntra scraper implementation - 2026 Version
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict
import time
import logging
import re
import random
from .base_scraper import BaseScraper

class MyntraScraper(BaseScraper):
    """Scraper for Myntra.com with robust URL extraction and Anti-Bot bypass"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        super().__init__(headless, timeout)
        self.platform = "Myntra"
        self.base_url = "https://www.myntra.com"
        self.logger = logging.getLogger('ShopEasy')
    
    def _apply_stealth_settings(self):
        """Standard stealth injection to reduce bot detection"""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": ua})
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        results = []
        try:
            self._apply_stealth_settings()
            # Myntra search URL format
            search_url = f"{self.base_url}/{product_name.replace(' ', '-')}"
            self.logger.info(f"Searching Myntra for: {product_name}")
            self.driver.get(search_url)
            
            # Wait for product base container
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'product-base'))
            )
            
            # Random scroll to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(random.uniform(1.5, 3.0))

            product_elements = self.driver.find_elements(By.CLASS_NAME, 'product-base')
            
            for element in product_elements:
                if len(results) >= max_results:
                    break
                
                try:
                    # Title (Usually Brand + Product Name)
                    brand = element.find_element(By.CLASS_NAME, 'product-brand').text.strip()
                    product_name_text = element.find_element(By.CLASS_NAME, 'product-product').text.strip()
                    full_title = f"{brand} - {product_name_text}"

                    # Price
                    price_text = element.find_element(By.CLASS_NAME, 'product-discountedPrice').text
                    price = float(re.sub(r'[^\d]', '', price_text))

                    # URL Extraction (Myntra links are relative, we make them absolute)
                    link_elem = element.find_element(By.TAG_NAME, 'a')
                    relative_url = link_elem.get_attribute('href')
                    
                    # Ensure URL is absolute and cleaned
                    if relative_url.startswith('/'):
                        url = f"{self.base_url}{relative_url.split('?')[0]}"
                    else:
                        url = relative_url.split('?')[0]

                    if full_title and price > 0:
                        results.append({
                            'title': full_title[:150],
                            'price': price,
                            'url': url,
                            'platform': self.platform,
                            'rating': None,
                            'num_reviews': None
                        })
                except Exception as e:
                    continue

            self.logger.info(f"Extracted {len(results)} products from Myntra")
        except Exception as e:
            self.logger.error(f"Myntra Scraper Error: {str(e)}")
        
        return results