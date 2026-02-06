"""
Croma scraper implementation
"""
from selenium.webdriver.common.by import By
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
        """Search for product on Croma"""
        results = []
        try:
            search_url = f"{self.base_url}/search/?q={product_name.replace(' ', '%20')}"
            self.logger.debug(f"Loading Croma URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for products to load
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.cp-product, .product-item, [data-product-id]'))
                )
            except:
                self.logger.warning("Timeout waiting for Croma search results")
            
            time.sleep(2)  # Additional wait for dynamic content
            
            # Try multiple selectors for product containers
            product_elements = []
            selectors = [
                'div.cp-product',
                '.product-item',
                '[data-product-id]',
                '.cp-product-tile',
                'div[class*="product"]'
            ]
            
            for selector in selectors:
                try:
                    product_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if product_elements:
                        self.logger.debug(f"Found {len(product_elements)} products using selector: {selector}")
                        break
                except:
                    continue
            
            if not product_elements:
                self.logger.warning("No product elements found on Croma")
                return results
            
            product_elements = product_elements[:max_results]
            
            for idx, element in enumerate(product_elements):
                try:
                    # Extract title - try multiple selectors
                    title = None
                    title_selectors = [
                        'h3.product-title a',
                        '.cp-product-title a',
                        'a[data-product-title]',
                        'h3 a',
                        '.product-title',
                        'a[href*="/product/"]'
                    ]
                    
                    for title_sel in title_selectors:
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, title_sel)
                            title = title_elem.text.strip() or title_elem.get_attribute('title')
                            if title:
                                break
                        except:
                            continue
                    
                    if not title:
                        # Try getting from any link
                        try:
                            link_elem = element.find_element(By.CSS_SELECTOR, 'a[href*="/product/"]')
                            title = link_elem.get_attribute('title') or link_elem.text.strip()
                        except:
                            pass
                    
                    if not title:
                        self.logger.debug(f"Could not extract title for product {idx+1}")
                        continue
                    
                    # Extract URL
                    url = None
                    try:
                        link_elem = element.find_element(By.CSS_SELECTOR, 'h3.product-title a, .cp-product-title a, a[href*="/product/"]')
                        url = link_elem.get_attribute('href')
                        if url and not url.startswith('http'):
                            url = self.base_url + url
                    except:
                        pass
                    
                    if not url:
                        url = self.base_url
                    
                    # Extract price - try multiple selectors
                    price = 0.0
                    price_selectors = [
                        '.amount',
                        '.product-price',
                        '.cp-product-price',
                        '[data-price]',
                        '.price',
                        'span[class*="price"]'
                    ]
                    
                    for price_sel in price_selectors:
                        try:
                            price_elem = element.find_element(By.CSS_SELECTOR, price_sel)
                            price_text = price_elem.text or price_elem.get_attribute('data-price')
                            if price_text:
                                price = self.extract_price(price_text)
                                if price > 0:
                                    break
                        except:
                            continue
                    
                    # If still no price, try to find any price-like text
                    if price == 0:
                        try:
                            all_text = element.text
                            import re
                            price_matches = re.findall(r'[₹]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)', all_text)
                            if price_matches:
                                price = self.extract_price(price_matches[0])
                        except:
                            pass
                    
                    # Extract rating
                    rating = None
                    try:
                        rating_selectors = [
                            '.rating',
                            '.product-rating',
                            '[data-rating]',
                            '.cp-rating'
                        ]
                        for rating_sel in rating_selectors:
                            try:
                                rating_elem = element.find_element(By.CSS_SELECTOR, rating_sel)
                                rating_text = rating_elem.get_attribute('data-rating') or rating_elem.text
                                if rating_text:
                                    rating = float(rating_text)
                                    break
                            except:
                                continue
                    except:
                        pass
                    
                    # Add product even if price is 0 (for debugging)
                    if title:
                        product_data = {
                            'title': title[:200],
                            'price': price,
                            'url': url,
                            'platform': self.platform,
                            'rating': rating
                        }
                        results.append(product_data)
                        self.logger.debug(f"Extracted: {title[:50]}... - ₹{price}")
                    
                except Exception as e:
                    self.logger.debug(f"Error extracting product {idx+1}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(results)} products from Croma")
            
        except Exception as e:
            self.logger.error(f"Error scraping Croma: {str(e)}", exc_info=True)
        
        return results
