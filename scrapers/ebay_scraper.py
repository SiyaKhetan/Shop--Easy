"""
eBay scraper implementation
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict
import time
import logging
from .base_scraper import BaseScraper


class EbayScraper(BaseScraper):
    """Scraper for eBay.com"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        super().__init__(headless, timeout)
        self.platform = "eBay"
        self.base_url = "https://www.ebay.com"
        self.logger = logging.getLogger('ShopEasy')
    
    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        """Search for product on eBay"""
        results = []
        try:
            search_url = f"{self.base_url}/sch/i.html?_nkw={product_name.replace(' ', '+')}"
            self.logger.debug(f"Loading eBay URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for products to load
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'li.s-item, .srp-results li'))
                )
            except:
                self.logger.warning("Timeout waiting for eBay search results")
            
            time.sleep(2)  # Additional wait for dynamic content
            
            # Try multiple selectors for product containers
            product_elements = []
            selectors = [
                'li.s-item',
                '.srp-results li.s-item',
                'ul.srp-results li',
                'li[class*="s-item"]'
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
                self.logger.warning("No product elements found on eBay")
                return results
            
            product_elements = product_elements[:max_results + 1]  # +1 to account for first item being header
            
            for idx, element in enumerate(product_elements):
                try:
                    # Extract title - try multiple selectors
                    title = None
                    title_selectors = [
                        '.s-item__title',
                        'h3.s-item__title',
                        'a.s-item__link',
                        '.s-item__title span'
                    ]
                    
                    for title_sel in title_selectors:
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, title_sel)
                            title = title_elem.text.strip()
                            if title and not title.startswith('Shop on eBay'):
                                break
                        except:
                            continue
                    
                    if not title or title.startswith('Shop on eBay'):
                        continue
                    
                    # Extract URL
                    url = None
                    try:
                        link_elem = element.find_element(By.CSS_SELECTOR, '.s-item__link, a[href*="/itm/"]')
                        url = link_elem.get_attribute('href')
                    except:
                        pass
                    
                    if not url:
                        url = self.base_url
                    
                    # Extract price - try multiple selectors
                    price = 0.0
                    price_selectors = [
                        '.s-item__price',
                        'span.s-item__price',
                        '.s-item__detail--primary'
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
                            price_matches = re.findall(r'[$€£]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)', all_text)
                            if price_matches:
                                price = self.extract_price(price_matches[0])
                        except:
                            pass
                    
                    # Extract rating/reviews (optional)
                    rating = None
                    try:
                        rating_elem = element.find_element(By.CSS_SELECTOR, '.s-item__reviews-count, .s-item__etrs-text')
                        rating_text = rating_elem.text
                        # eBay shows review count, not rating directly
                        rating = None
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
                        self.logger.debug(f"Extracted: {title[:50]}... - ${price}")
                    
                except Exception as e:
                    self.logger.debug(f"Error extracting product {idx+1}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(results)} products from eBay")
            
        except Exception as e:
            self.logger.error(f"Error scraping eBay: {str(e)}", exc_info=True)
        
        return results
