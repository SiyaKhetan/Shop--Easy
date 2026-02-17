"""
Croma scraper implementation
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict
import time
import logging
from .base_scraper import BaseScraper


class CromaScraper(BaseScraper):
    """Scraper for Croma.com"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        super().__init__(headless, timeout)
        self.platform = "Croma"
        self.base_url = "https://www.croma.com"
        self.logger = logging.getLogger('ShopEasy')
    
    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        """Search for product on Croma using automated typing"""
        results = []
        try:
            self.logger.info(f"Navigating to Croma homepage...")
            self.driver.get(self.base_url)
            
            # 1. Wait for the search box to be visible and interactable
            wait = WebDriverWait(self.driver, self.timeout)
            try:
                # Croma's search ID is typically 'searchV2' or 'search'
                search_box = wait.until(EC.element_to_be_clickable((By.ID, "searchV2")))
            except:
                # Fallback to general search input if ID changed
                search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='search'], #search")))

            # 2. Automate the typing and searching
            self.logger.debug(f"Typing product name: {product_name}")
            search_box.clear()
            search_box.send_keys(product_name)
            search_box.send_keys(Keys.ENTER)
            
            # 3. Wait for the results page to load
            # We look for the product list container
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.cp-product, .product-item, .plp-card-main')))
            except:
                self.logger.warning("Timeout waiting for Croma results to appear")

            time.sleep(3)  # Extra buffer for images and prices to render
            
            # --- START SCRAPING LOGIC ---
            
            product_elements = []
            selectors = [
                'div.cp-product', 
                '.product-item', 
                '.plp-card-main',
                '[data-product-id]'
            ]
            
            for selector in selectors:
                product_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if product_elements:
                    self.logger.debug(f"Found {len(product_elements)} products using: {selector}")
                    break
            
            if not product_elements:
                return results
            
            for idx, element in enumerate(product_elements[:max_results]):
                try:
                    # Extract Title
                    title = "N/A"
                    title_selectors = ['h3.product-title', '.plp-product-title', '.cp-product-title', 'h3']
                    for t_sel in title_selectors:
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, t_sel)
                            title = title_elem.text.strip()
                            if title: break
                        except: continue

                    # Extract Price
                    price = 0.0
                    price_selectors = ['.amount', '.new-price', '.cp-price', '.pdp-price']
                    for p_sel in price_selectors:
                        try:
                            price_text = element.find_element(By.CSS_SELECTOR, p_sel).text
                            price = self.extract_price(price_text)
                            if price > 0: break
                        except: continue

                    # Extract URL
                    url = self.base_url
                    try:
                        url = element.find_element(By.TAG_NAME, 'a').get_attribute('href')
                    except: pass

                    if title != "N/A":
                        results.append({
                            'title': title,
                            'price': price,
                            'url': url,
                            'platform': self.platform,
                            'rating': None # Croma ratings are often lazily loaded via JS
                        })

                except Exception as e:
                    continue

            self.logger.info(f"Croma: Extracted {len(results)} items")
            
        except Exception as e:
            self.logger.error(f"Croma Error: {str(e)}")
        
        return results