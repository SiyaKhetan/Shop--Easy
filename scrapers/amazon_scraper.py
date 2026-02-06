"""
Amazon scraper implementation
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict
import time
import logging
from .base_scraper import BaseScraper


class AmazonScraper(BaseScraper):
    """Scraper for Amazon.in"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        super().__init__(headless, timeout)
        self.platform = "Amazon"
        self.base_url = "https://www.amazon.in"
        self.logger = logging.getLogger('ShopEasy')
    
    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        """Search for product on Amazon"""
        results = []
        try:
            search_url = f"{self.base_url}/s?k={product_name.replace(' ', '+')}"
            self.logger.debug(f"Loading Amazon URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for page to load - wait for search results container
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"], .s-result-item, [data-asin]'))
                )
            except:
                self.logger.warning("Timeout waiting for Amazon search results")
            
            time.sleep(2)  # Additional wait for dynamic content
            
            # Try multiple selectors for product containers
            product_elements = []
            selectors = [
                'div[data-component-type="s-search-result"]',
                'div[data-asin]:not([data-asin=""])',
                '.s-result-item[data-asin]',
                'div.s-result-item'
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
                self.logger.warning("No product elements found on Amazon")
                return results
            
            product_elements = product_elements[:max_results]
            
            for idx, element in enumerate(product_elements):
                try:
                    # Extract title - try multiple selectors
                    title = None
                    title_selectors = [
                        'h2 a span.a-text-normal',
                        'h2 a span',
                        'h2 span',
                        'a.a-link-normal span',
                        '.s-title-instructions-style h2 a span'
                    ]
                    
                    for title_sel in title_selectors:
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, title_sel)
                            title = title_elem.text.strip()
                            if title:
                                break
                        except:
                            continue
                    
                    if not title:
                        # Try getting from link
                        try:
                            link_elem = element.find_element(By.CSS_SELECTOR, 'h2 a, a.a-link-normal')
                            title = link_elem.get_attribute('title') or link_elem.text.strip()
                        except:
                            pass
                    
                    if not title:
                        self.logger.debug(f"Could not extract title for product {idx+1}")
                        continue
                    
                    # Extract URL
                    url = None
                    try:
                        link_elem = element.find_element(By.CSS_SELECTOR, 'h2 a, a.a-link-normal')
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
                        '.a-price-whole',
                        '.a-price .a-offscreen',
                        'span.a-price-whole',
                        '[data-a-color="price"] .a-offscreen',
                        '.a-price[data-a-color="price"] .a-offscreen',
                        'span.a-price',
                        '.a-price-symbol + .a-price-whole'
                    ]
                    
                    for price_sel in price_selectors:
                        try:
                            price_elem = element.find_element(By.CSS_SELECTOR, price_sel)
                            price_text = price_elem.text or price_elem.get_attribute('textContent') or price_elem.get_attribute('innerText') or price_elem.get_attribute('aria-label')
                            if price_text:
                                price = self.extract_price(price_text)
                                if price > 0:
                                    break
                        except:
                            continue
                    
                    # If still no price, try to find any price-like text in the element
                    if price == 0:
                        try:
                            all_text = element.text
                            # Look for price patterns like ₹12,345 or 12345
                            import re
                            price_matches = re.findall(r'[₹$]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)', all_text)
                            if price_matches:
                                price = self.extract_price(price_matches[0])
                        except:
                            pass
                    
                    # Extract rating (optional)
                    rating = None
                    try:
                        rating_selectors = [
                            '.a-icon-alt',
                            '[aria-label*="out of"]',
                            '.a-icon-star'
                        ]
                        for rating_sel in rating_selectors:
                            try:
                                rating_elem = element.find_element(By.CSS_SELECTOR, rating_sel)
                                rating_text = rating_elem.get_attribute('innerHTML') or rating_elem.get_attribute('aria-label') or rating_elem.text
                                if rating_text:
                                    import re
                                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                                    if rating_match:
                                        rating = float(rating_match.group(1))
                                        break
                            except:
                                continue
                    except:
                        pass
                    
                    # Add product even if price is 0 (for debugging)
                    if title:
                        product_data = {
                            'title': title[:200],  # Limit title length
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
            
            self.logger.info(f"Successfully extracted {len(results)} products from Amazon")
            
        except Exception as e:
            self.logger.error(f"Error scraping Amazon: {str(e)}", exc_info=True)
        
        return results
