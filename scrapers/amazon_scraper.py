"""
Amazon scraper implementation - Ultimate Link Extraction Fix
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
    """Scraper for Amazon.in with robust URL extraction and Anti-Bot bypass"""
    
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
        """Wait for page to fully load"""
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-component-type="s-search-result"], .s-result-item'))
            )
            time.sleep(random.uniform(2.0, 4.0))
            self.driver.execute_script("window.scrollTo(0, 400);")
        except Exception as e:
            self.logger.debug(f"Page load wait timed out: {str(e)}")

    def _is_valid_product(self, element) -> bool:
        """Check if element is a valid product"""
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
        """Overhauled URL extraction to ensure valid product links"""
        url = None
        try:
            # 1. Try the main heading link (standard Amazon structure)
            link_selectors = ['h2 a', 'a.a-link-normal.s-underline-text', 'a.a-link-normal']
            for selector in link_selectors:
                try:
                    found_link = element.find_element(By.CSS_SELECTOR, selector)
                    url = found_link.get_attribute('href')
                    if url and '/dp/' in url: break
                except: continue

            # 2. Fallback: Search the entire product element for any link containing /dp/
            if not url or '/dp/' not in url:
                all_links = element.find_elements(By.TAG_NAME, 'a')
                for l in all_links:
                    potential_url = l.get_attribute('href')
                    if potential_url and '/dp/' in potential_url:
                        url = potential_url
                        break

            # 3. Final Fallback: Use the ASIN to build a direct URL
            if not url or '/dp/' not in url:
                asin = element.get_attribute('data-asin')
                if asin:
                    url = f"{self.base_url}/dp/{asin}"

            # Clean tracking parameters
            if url:
                clean_match = re.search(r'(https?://[^/]+(?:/dp/|/gp/product/)[A-Z0-9]+)', url)
                return clean_match.group(1) if clean_match else url.split('?')[0]
                
        except Exception as e:
            self.logger.debug(f"URL Extraction Error: {e}")
        return self.base_url

    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        results = []
        try:
            self._apply_stealth_settings()
            search_url = f"{self.base_url}/s?k={product_name.replace(' ', '+')}"
            self.driver.get(search_url)
            
            if "captcha" in self.driver.page_source.lower():
                self.logger.error("Blocked by CAPTCHA")
                return []

            self._wait_for_page_load()
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-component-type="s-search-result"]')
            
            for element in product_elements:
                if len(results) >= max_results: break
                if not self._is_valid_product(element): continue

                title = self._extract_title(element)
                price = self._extract_price(element)
                url = self._extract_url(element) # Overhauled method

                if title and price > 0:
                    results.append({
                        'title': title[:150],
                        'price': price,
                        'url': url,
                        'platform': self.platform,
                        'rating': None,
                        'num_reviews': None
                    })
        except Exception as e:
            self.logger.error(f"Scraper error: {str(e)}")
        return results