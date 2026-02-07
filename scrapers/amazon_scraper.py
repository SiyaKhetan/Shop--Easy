"""
Amazon scraper implementation - Improved version with better accuracy
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict
import time
import logging
import re
from .base_scraper import BaseScraper


class AmazonScraper(BaseScraper):
    """Scraper for Amazon.in with improved accuracy"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        super().__init__(headless, timeout)
        self.platform = "Amazon"
        self.base_url = "https://www.amazon.in"
        self.logger = logging.getLogger('ShopEasy')
    
    def _wait_for_page_load(self):
        """Wait for page to fully load"""
        try:
            # Wait for search results container
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"], .s-result-item, [data-asin]:not([data-asin=""])'))
            )
            time.sleep(2)  # Wait for dynamic content
            
            # Scroll to load more products
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        except Exception as e:
            self.logger.debug(f"Page load wait completed with: {str(e)}")
    
    def _is_valid_product(self, element) -> bool:
        """Check if element is a valid product (not ad/sponsored)"""
        try:
            # Check for sponsored/ad indicators
            element_text = element.text.lower()
            if any(keyword in element_text for keyword in ['sponsored', 'advertisement', 'ad']):
                return False
            
            # Check if it has required product attributes
            has_asin = element.get_attribute('data-asin') and element.get_attribute('data-asin') != ''
            has_title = len(element.find_elements(By.CSS_SELECTOR, 'h2 a, h2 span, a.a-link-normal')) > 0
            
            return has_asin and has_title
        except:
            return False
    
    def _extract_title(self, element) -> str:
        """Extract product title with multiple fallback strategies"""
        title = None
        
        # Strategy 1: Modern Amazon selectors
        title_selectors = [
            'h2 a.a-link-normal span.a-text-normal',
            'h2 a span.a-text-normal',
            'h2 a span',
            'h2 span.a-text-normal',
            'a.a-link-normal.a-text-normal span',
            '.s-title-instructions-style h2 a span',
            'h2 a',
            'a.a-link-normal[href*="/dp/"] span',
            'a.a-link-normal[href*="/gp/product/"] span'
        ]
        
        for selector in title_selectors:
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, selector)
                title = title_elem.text.strip()
                if title and len(title) > 5:  # Valid title should be meaningful
                    return title
            except:
                continue
        
        # Strategy 2: Get from link title attribute
        try:
            link_elem = element.find_element(By.CSS_SELECTOR, 'h2 a, a.a-link-normal[href*="/dp/"], a.a-link-normal[href*="/gp/product/"]')
            title = link_elem.get_attribute('title') or link_elem.get_attribute('aria-label')
            if title and len(title) > 5:
                return title.strip()
        except:
            pass
        
        # Strategy 3: Get from any link in the element
        try:
            links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/dp/"], a[href*="/gp/product/"]')
            for link in links:
                title = link.get_attribute('title') or link.text.strip()
                if title and len(title) > 5:
                    return title
        except:
            pass
        
        return None
    
    def _extract_url(self, element) -> str:
        """Extract product URL"""
        url_selectors = [
            'h2 a',
            'a.a-link-normal[href*="/dp/"]',
            'a.a-link-normal[href*="/gp/product/"]',
            'a[href*="/dp/"]',
            'a[href*="/gp/product/"]'
        ]
        
        for selector in url_selectors:
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, selector)
                url = link_elem.get_attribute('href')
                if url:
                    # Clean URL (remove tracking parameters)
                    if '/dp/' in url or '/gp/product/' in url:
                        # Extract base URL
                        url_match = re.search(r'(https?://[^/]+(/dp/|/gp/product/)[A-Z0-9]+)', url)
                        if url_match:
                            return url_match.group(1)
                        return url.split('?')[0]  # Remove query parameters
            except:
                continue
        
        return self.base_url
    
    def _extract_price(self, element) -> float:
        """Extract price with multiple strategies"""
        price = 0.0
        
        # Strategy 1: Modern Amazon price selectors
        price_selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            'span.a-price-whole',
            '.a-price[data-a-color="price"] .a-offscreen',
            '[data-a-color="price"] .a-offscreen',
            'span.a-price',
            '.a-price-symbol + .a-price-whole',
            '.a-price .a-price-whole',
            'span[data-a-color="price"]',
            '.a-price-range .a-offscreen',
            '.a-price-range span'
        ]
        
        for selector in price_selectors:
            try:
                price_elem = element.find_element(By.CSS_SELECTOR, selector)
                price_text = (price_elem.text or 
                            price_elem.get_attribute('textContent') or 
                            price_elem.get_attribute('innerText') or 
                            price_elem.get_attribute('aria-label') or
                            price_elem.get_attribute('data-a-color'))
                
                if price_text:
                    price = self.extract_price(price_text)
                    if price > 0:
                        return price
            except:
                continue
        
        # Strategy 2: Look for price in all text
        try:
            all_text = element.text
            # Look for price patterns: ₹12,345 or ₹12,345.67
            price_patterns = [
                r'₹\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)',
                r'Rs\.?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)',
                r'INR\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)',
                r'(\d{1,3}(?:[,\s]\d{3})+(?:\.\d{2})?)'  # Generic number with commas
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, all_text)
                if matches:
                    # Take the first reasonable price (usually the main price)
                    for match in matches:
                        price = self.extract_price(match.replace(',', '').replace(' ', ''))
                        if price > 10:  # Reasonable minimum price
                            return price
        except:
            pass
        
        return 0.0
    
    def _extract_rating(self, element) -> float:
        """Extract product rating"""
        rating = None
        
        # Strategy 1: Rating from aria-label or text
        rating_selectors = [
            '.a-icon-alt',
            '[aria-label*="out of"]',
            '[aria-label*="stars"]',
            '.a-icon-star',
            '.a-icon-star-small',
            'span[aria-label*="out of"]',
            'i[aria-label*="out of"]'
        ]
        
        for selector in rating_selectors:
            try:
                rating_elem = element.find_element(By.CSS_SELECTOR, selector)
                rating_text = (rating_elem.get_attribute('aria-label') or 
                             rating_elem.get_attribute('innerHTML') or 
                             rating_elem.text)
                
                if rating_text:
                    # Extract rating number (e.g., "4.5 out of 5" -> 4.5)
                    rating_match = re.search(r'(\d+\.?\d*)\s*(?:out of|stars|star)', rating_text, re.IGNORECASE)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        if 0 <= rating <= 5:
                            return rating
                    
                    # Try simple number extraction
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        if 0 <= rating <= 5:
                            return rating
            except:
                continue
        
        return None
    
    def _extract_num_reviews(self, element) -> int:
        """Extract number of reviews"""
        try:
            # Look for review count text
            review_selectors = [
                'a[href*="#customerReviews"] span',
                '.a-size-base',
                'span[aria-label*="ratings"]',
                'a[href*="customerReviews"]'
            ]
            
            for selector in review_selectors:
                try:
                    review_elem = element.find_element(By.CSS_SELECTOR, selector)
                    review_text = review_elem.text or review_elem.get_attribute('aria-label') or ''
                    
                    # Extract number from text like "1,234 ratings" or "1234"
                    review_match = re.search(r'([\d,]+)', review_text.replace(',', ''))
                    if review_match:
                        num_reviews = int(review_match.group(1).replace(',', ''))
                        if num_reviews > 0:
                            return num_reviews
                except:
                    continue
        except:
            pass
        
        return None
    
    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        """Search for product on Amazon with improved accuracy"""
        results = []
        try:
            search_url = f"{self.base_url}/s?k={product_name.replace(' ', '+')}"
            self.logger.debug(f"Loading Amazon URL: {search_url}")
            self.driver.get(search_url)
            
            # Wait for page to load
            self._wait_for_page_load()
            
            # Try multiple selectors for product containers
            product_elements = []
            selectors = [
                'div[data-component-type="s-search-result"][data-asin]:not([data-asin=""])',
                'div[data-asin]:not([data-asin=""])',
                '.s-result-item[data-asin]:not([data-asin=""])',
                'div[data-component-type="s-search-result"]',
                'div.s-result-item'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    # Filter valid products
                    valid_elements = [e for e in elements if self._is_valid_product(e)]
                    if valid_elements:
                        product_elements = valid_elements
                        self.logger.debug(f"Found {len(product_elements)} valid products using selector: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"Selector {selector} failed: {str(e)}")
                    continue
            
            if not product_elements:
                self.logger.warning("No product elements found on Amazon")
                return results
            
            # Limit to max_results
            product_elements = product_elements[:max_results * 2]  # Get more to filter
            
            for idx, element in enumerate(product_elements):
                if len(results) >= max_results:
                    break
                    
                try:
                    # Extract title
                    title = self._extract_title(element)
                    if not title:
                        self.logger.debug(f"Could not extract title for product {idx+1}")
                        continue
                    
                    # Extract URL
                    url = self._extract_url(element)
                    
                    # Extract price
                    price = self._extract_price(element)
                    
                    # Extract rating
                    rating = self._extract_rating(element)
                    
                    # Extract number of reviews
                    num_reviews = self._extract_num_reviews(element)
                    
                    # Only add products with valid price
                    if price > 0:
                        product_data = {
                            'title': title[:200],  # Limit title length
                            'price': price,
                            'url': url,
                            'platform': self.platform,
                            'rating': rating,
                            'num_reviews': num_reviews
                        }
                        results.append(product_data)
                        self.logger.debug(f"Extracted: {title[:50]}... - ₹{price} (Rating: {rating}, Reviews: {num_reviews})")
                    else:
                        self.logger.debug(f"Skipping product {idx+1} - no valid price found")
                    
                except Exception as e:
                    self.logger.debug(f"Error extracting product {idx+1}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(results)} products from Amazon")
            
        except Exception as e:
            self.logger.error(f"Error scraping Amazon: {str(e)}", exc_info=True)
        
        return results
