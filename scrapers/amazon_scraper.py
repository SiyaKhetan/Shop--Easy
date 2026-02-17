"""
Amazon scraper implementation - Fixed Stealth Version with Correct Link Extraction
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

class AmazonScraper(BaseScraper):
    """Scraper for Amazon.in with improved accuracy and Anti-Bot bypass"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        super().__init__(headless, timeout)
        self.platform = "Amazon"
        self.base_url = "https://www.amazon.in"
        self.logger = logging.getLogger('ShopEasy')
    
    def _apply_stealth_settings(self):
        """Inject scripts to hide Selenium and set a realistic User-Agent"""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": ua})
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
        })

    def _wait_for_page_load(self):
        """Wait for page to fully load with human-like randomized delays"""
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-component-type="s-search-result"], .s-result-item'))
            )
            time.sleep(random.uniform(2.0, 4.0)) 
            self.driver.execute_script("window.scrollTo(0, 400);")
            time.sleep(1)
        except Exception as e:
            self.logger.debug(f"Page load wait timed out: {str(e)}")

    def _is_valid_product(self, element) -> bool:
        """Check if element is a valid product (not ad/sponsored)"""
        try:
            is_sponsored = element.find_elements(By.XPATH, ".//span[contains(text(), 'Sponsored')]") or \
                           element.find_elements(By.XPATH, ".//span[contains(text(), 'Ad')]")
            if is_sponsored:
                return False
            asin = element.get_attribute('data-asin')
            return asin is not None and len(asin) > 0
        except:
            return False

    def _extract_title(self, element) -> str:
        title_selectors = ['h2 a span.a-text-normal', 'h2 span.a-text-normal', '.a-size-medium.a-color-base.a-text-normal']
        for selector in title_selectors:
            try:
                text = element.find_element(By.CSS_SELECTOR, selector).text.strip()
                if text: return text
            except: continue
        return None

    def _extract_price(self, element) -> float:
        try:
            price_whole = element.find_element(By.CSS_SELECTOR, '.a-price-whole').text
            price_clean = re.sub(r'[^\d]', '', price_whole)
            return float(price_clean) if price_clean else 0.0
        except:
            return 0.0

    def _extract_url(self, element) -> str:
        """Robustly extract and clean the product URL"""
        try:
            # Look for the primary link in the heading
            link_elem = element.find_element(By.CSS_SELECTOR, 'h2 a')
            url = link_elem.get_attribute('href')
            
            # If the primary link is missing or invalid, find any product link within the item
            if not url or '/dp/' not in url:
                potential_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/dp/"], a[href*="/gp/product/"]')
                if potential_links:
                    url = potential_links[0].get_attribute('href')

            if url:
                # Clean URL: Extract the base product path and remove tracking/search parameters
                # This ensures the link is short and direct
                clean_match = re.search(r'(https?://[^/]+(?:/dp/|/gp/product/)[A-Z0-9]+)', url)
                if clean_match:
                    return clean_match.group(1)
                return url.split('?')[0]
        except:
            pass
        return self.base_url

    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        """Search for product on Amazon with improved accuracy"""
        results = []
        try:
            self._apply_stealth_settings()
            search_url = f"{self.base_url}/s?k={product_name.replace(' ', '+')}"
            self.logger.info(f"Searching Amazon for: {product_name}")
            self.driver.get(search_url)
            
            if "captcha" in self.driver.page_source.lower() or "robot" in self.driver.title.lower():
                self.logger.error("Amazon blocked the request with a CAPTCHA.")
                return []

            self._wait_for_page_load()
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]')
            
            for element in product_elements:
                if len(results) >= max_results:
                    break
                
                if not self._is_valid_product(element):
                    continue

                title = self._extract_title(element)
                price = self._extract_price(element)
                url = self._extract_url(element) # Using the new robust method

                if title and price > 0:
                    results.append({
                        'title': title[:150],
                        'price': price,
                        'url': url,
                        'platform': self.platform,
                        'rating': None,
                        'num_reviews': None
                    })

            self.logger.info(f"Extracted {len(results)} products from Amazon")
        except Exception as e:
            self.logger.error(f"Error scraping Amazon: {str(e)}")
        
        return results