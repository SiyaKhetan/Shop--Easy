"""
Flipkart scraper implementation
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict
import time
import logging
from .base_scraper import BaseScraper


class FlipkartScraper(BaseScraper):
    """Scraper for Flipkart.com"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        super().__init__(headless, timeout)
        self.platform = "Flipkart"
        self.base_url = "https://www.flipkart.com"
        self.logger = logging.getLogger('ShopEasy')
    
    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        """Search for product on Flipkart"""
        results = []
        try:
            search_url = f"{self.base_url}/search?q={product_name.replace(' ', '%20')}"
            self.logger.debug(f"Loading Flipkart URL: {search_url}")
            self.driver.get(search_url)
            time.sleep(2)
            
            # Close login popup if present - try multiple selectors
            popup_selectors = [
                'button._2KpZ6l._2doB4z',
                'button[class*="_2doB4z"]',
                'span[class*="_2doB4z"]',
                'button:contains("✕")'
            ]
            
            for popup_sel in popup_selectors:
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, popup_sel)
                    if close_btn.is_displayed():
                        close_btn.click()
                        time.sleep(1)
                        break
                except:
                    continue
            
            # Wait for products to load
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-id], ._1AtVbE, ._13oc-S'))
                )
            except:
                self.logger.warning("Timeout waiting for Flipkart search results")
            
            time.sleep(2)  # Additional wait for dynamic content
            
            # Try multiple selectors for product containers
            product_elements = []
            selectors = [
                'div[data-id]',
                '._1AtVbE',
                '._13oc-S',
                'div[class*="_1AtVbE"]',
                'div[class*="_13oc-S"]'
            ]
            
            for selector in selectors:
                try:
                    product_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if product_elements and len(product_elements) > 1:  # Filter out single container divs
                        self.logger.debug(f"Found {len(product_elements)} products using selector: {selector}")
                        break
                except:
                    continue
            
            if not product_elements:
                self.logger.warning("No product elements found on Flipkart")
                return results
            
            product_elements = product_elements[:max_results]
            
            for idx, element in enumerate(product_elements):
                try:
                    # Extract title - try multiple selectors
                    title = None
                    title_selectors = [
                        'a._1fQZEK',
                        'a.s1Q9rs',
                        'a[class*="_1fQZEK"]',
                        'a[class*="s1Q9rs"]',
                        'div[class*="_4rR01T"]',
                        'a[title]'
                    ]
                    
                    for title_sel in title_selectors:
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, title_sel)
                            title = title_elem.get_attribute('title') or title_elem.text.strip()
                            if title:
                                break
                        except:
                            continue
                    
                    if not title:
                        # Try getting from any link
                        try:
                            link_elem = element.find_element(By.CSS_SELECTOR, 'a')
                            title = link_elem.get_attribute('title') or link_elem.text.strip()
                        except:
                            pass
                    
                    if not title:
                        self.logger.debug(f"Could not extract title for product {idx+1}")
                        continue
                    
                    # Extract URL
                    url = None
                    try:
                        link_elem = element.find_element(By.CSS_SELECTOR, 'a._1fQZEK, a.s1Q9rs, a[href*="/p/"]')
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
                        '._30jeq3',
                        '._25b18c',
                        'div._30jeq3',
                        '[class*="_30jeq3"]',
                        'div[class*="_25b18c"]',
                        '._1_WHN1'
                    ]
                    
                    for price_sel in price_selectors:
                        try:
                            price_elem = element.find_element(By.CSS_SELECTOR, price_sel)
                            price_text = price_elem.text
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
                            '._3LWZlK',
                            'div[class*="_3LWZlK"]',
                            'span[class*="_3LWZlK"]'
                        ]
                        for rating_sel in rating_selectors:
                            try:
                                rating_elem = element.find_element(By.CSS_SELECTOR, rating_sel)
                                rating_text = rating_elem.text
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
            
            self.logger.info(f"Successfully extracted {len(results)} products from Flipkart")
            
        except Exception as e:
            self.logger.error(f"Error scraping Flipkart: {str(e)}", exc_info=True)
        
        return results
