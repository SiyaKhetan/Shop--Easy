"""
Flipkart scraper implementation - Improved version with better accuracy
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from typing import List, Dict
import time
import logging
import re
from .base_scraper import BaseScraper


class FlipkartScraper(BaseScraper):
    """Scraper for Flipkart.com with improved accuracy"""
    
    def __init__(self, headless: bool = False, timeout: int = 30):
        super().__init__(headless, timeout)
        self.platform = "Flipkart"
        self.base_url = "https://www.flipkart.com"
        self.logger = logging.getLogger('ShopEasy')
    
    def _close_popups(self):
        """Close login popups and other overlays"""
        time.sleep(1)  # Wait a bit for popup to appear
        
        popup_selectors = [
            'button._2KpZ6l._2doB4z',  # Close button
            'button[class*="_2doB4z"]',
            'span[class*="_2doB4z"]',
            'button._2doB4z',
            'span._2doB4z',
            '[class*="close"]',
            'button[aria-label*="Close"]',
            'button[aria-label*="close"]'
        ]
        
        for popup_sel in popup_selectors:
            try:
                close_btn = self.driver.find_element(By.CSS_SELECTOR, popup_sel)
                if close_btn.is_displayed():
                    close_btn.click()
                    time.sleep(1)
                    self.logger.debug("Closed popup")
                    break
            except:
                continue
        
        # Try to close any modal/overlay by pressing Escape
        try:
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except:
            pass
    
    def _wait_for_page_load(self):
        """Wait for page to fully load"""
        try:
            # Wait for any product-related elements (more lenient)
            WebDriverWait(self.driver, self.timeout).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-id]')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/p/"]')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[class*="_1AtVbE"]')),
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[class*="_13oc-S"]'))
                )
            )
            time.sleep(3)  # Wait for dynamic content
            
            # Scroll to load more products
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/4);")
            time.sleep(1.5)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        except TimeoutException:
            self.logger.warning("Timeout waiting for Flipkart search results - continuing anyway")
        except Exception as e:
            self.logger.debug(f"Page load wait completed with: {str(e)}")
    
    def _is_valid_product(self, element) -> bool:
        """Check if element is a valid product container - more lenient"""
        try:
            # Check if it has a product link (most reliable indicator)
            has_link = len(element.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')) > 0
            
            # Check for product title elements (various possible selectors)
            has_title_elem = len(element.find_elements(By.CSS_SELECTOR, 
                'a[href*="/p/"], div[class*="_4rR01T"], a[class*="_1fQZEK"], a[class*="s1Q9rs"]')) > 0
            
            # Check for data-id (optional, not required)
            has_data_id = element.get_attribute('data-id') is not None
            
            # Exclude obvious ads
            element_text = element.text.lower()
            if any(keyword in element_text for keyword in ['advertisement', 'ad', 'sponsored']):
                return False
            
            # More lenient: just need a product link OR (data-id AND title element)
            return has_link or (has_data_id and has_title_elem)
        except:
            return False
    
    def _extract_title(self, element) -> str:
        """Extract product title with multiple fallback strategies"""
        title = None
        
        # Strategy 1: Try to find product link first (most reliable)
        try:
            product_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
            for link in product_links:
                title = link.get_attribute('title') or link.text.strip()
                if title and len(title) > 5:
                    return title
        except:
            pass
        
        # Strategy 2: Modern Flipkart selectors
        title_selectors = [
            'a._1fQZEK',  # Product link
            'a.s1Q9rs',   # Alternative product link
            'div._4rR01T', # Title div
            'a[class*="_1fQZEK"]',
            'a[class*="s1Q9rs"]',
            'div[class*="_4rR01T"]',
            'a[title]'
        ]
        
        for selector in title_selectors:
            try:
                title_elem = element.find_element(By.CSS_SELECTOR, selector)
                title = title_elem.get_attribute('title') or title_elem.text.strip()
                if title and len(title) > 5:
                    return title
            except:
                continue
        
        # Strategy 3: Get from any link with product URL
        try:
            links = element.find_elements(By.CSS_SELECTOR, 'a')
            for link in links:
                href = link.get_attribute('href') or ''
                if '/p/' in href:
                    title = link.get_attribute('title') or link.text.strip()
                    if title and len(title) > 5:
                        return title
        except:
            pass
        
        # Strategy 4: Get from any text element (last resort)
        try:
            text_elements = element.find_elements(By.CSS_SELECTOR, 'div, span, a')
            for elem in text_elements:
                text = elem.text.strip()
                if text and 10 < len(text) < 200:  # Reasonable title length
                    # Check if it looks like a product title (not price, rating, etc.)
                    if not re.match(r'^[₹\d,.\s]+$', text):  # Not just numbers/currency
                        if '₹' not in text or len(text) > 20:  # Either no price or long enough
                            return text
        except:
            pass
        
        return None
    
    def _extract_url(self, element) -> str:
        """Extract product URL"""
        # First try product links
        try:
            product_links = element.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
            for link in product_links:
                url = link.get_attribute('href')
                if url:
                    # Clean URL (remove tracking parameters)
                    if '/p/' in url:
                        url_match = re.search(r'(https?://[^/]+/p/[^?]+)', url)
                        if url_match:
                            return url_match.group(1)
                        return url.split('?')[0]  # Remove query parameters
                    return url
        except:
            pass
        
        # Fallback to other selectors
        url_selectors = [
            'a._1fQZEK',
            'a.s1Q9rs',
            'a[class*="_1fQZEK"]',
            'a[class*="s1Q9rs"]'
        ]
        
        for selector in url_selectors:
            try:
                link_elem = element.find_element(By.CSS_SELECTOR, selector)
                url = link_elem.get_attribute('href')
                if url and '/p/' in url:
                    url_match = re.search(r'(https?://[^/]+/p/[^?]+)', url)
                    if url_match:
                        return url_match.group(1)
                    return url.split('?')[0]
            except:
                continue
        
        return self.base_url
    
    def _extract_price(self, element) -> float:
        """Extract price with multiple strategies"""
        price = 0.0
        
        # Strategy 1: Modern Flipkart price selectors
        price_selectors = [
            '._30jeq3',  # Main price
            '._25b18c',  # Alternative price
            'div._30jeq3',
            '[class*="_30jeq3"]',
            'div[class*="_25b18c"]',
            '._1_WHN1',  # Price in some layouts
            'div[class*="_1_WHN1"]',
            'span._30jeq3',
            'div._16Jk6d'  # Price in grid view
        ]
        
        for selector in price_selectors:
            try:
                price_elem = element.find_element(By.CSS_SELECTOR, selector)
                price_text = price_elem.text
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
        
        # Strategy 1: Rating from text
        rating_selectors = [
            '._3LWZlK',  # Rating element
            'div[class*="_3LWZlK"]',
            'span[class*="_3LWZlK"]',
            'div._2d4LTz',  # Alternative rating
            '[class*="_2d4LTz"]',
            'div[aria-label*="rated"]',
            'span[aria-label*="rated"]'
        ]
        
        for selector in rating_selectors:
            try:
                rating_elem = element.find_element(By.CSS_SELECTOR, selector)
                rating_text = rating_elem.text or rating_elem.get_attribute('aria-label') or ''
                
                if rating_text:
                    # Extract rating number (e.g., "4.5" or "4.5 out of 5")
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        if 0 <= rating <= 5:
                            return rating
            except:
                continue
        
        # Strategy 2: Look for rating in aria-label
        try:
            rating_elems = element.find_elements(By.CSS_SELECTOR, '[aria-label*="rated"], [aria-label*="star"]')
            for rating_elem in rating_elems:
                aria_label = rating_elem.get_attribute('aria-label') or ''
                rating_match = re.search(r'(\d+\.?\d*)', aria_label)
                if rating_match:
                    rating = float(rating_match.group(1))
                    if 0 <= rating <= 5:
                        return rating
        except:
            pass
        
        return None
    
    def _extract_num_reviews(self, element) -> int:
        """Extract number of reviews"""
        try:
            # Look for review count text
            review_selectors = [
                'span._2_R_DZ',  # Review count
                'span[class*="_2_R_DZ"]',
                'div._2_R_DZ',
                'span[class*="reviews"]',
                'a[href*="reviews"]'
            ]
            
            for selector in review_selectors:
                try:
                    review_elem = element.find_element(By.CSS_SELECTOR, selector)
                    review_text = review_elem.text or review_elem.get_attribute('aria-label') or ''
                    
                    # Extract number from text like "1,234 Reviews" or "1234"
                    review_match = re.search(r'([\d,]+)', review_text.replace(',', ''))
                    if review_match:
                        num_reviews = int(review_match.group(1).replace(',', ''))
                        if num_reviews > 0:
                            return num_reviews
                except:
                    continue
            
            # Also check in all text
            try:
                all_text = element.text
                review_match = re.search(r'([\d,]+)\s*(?:reviews?|ratings?)', all_text, re.IGNORECASE)
                if review_match:
                    num_reviews = int(review_match.group(1).replace(',', ''))
                    if num_reviews > 0:
                        return num_reviews
            except:
                pass
        except:
            pass
        
        return None
    
    def search_product(self, product_name: str, max_results: int = 5) -> List[Dict]:
        """Search for product on Flipkart with improved accuracy"""
        results = []
        try:
            search_url = f"{self.base_url}/search?q={product_name.replace(' ', '%20')}"
            self.logger.debug(f"Loading Flipkart URL: {search_url}")
            self.driver.get(search_url)
            time.sleep(3)  # Initial wait
            
            # Close popups
            self._close_popups()
            
            # Wait for page to load
            self._wait_for_page_load()
            
            # Try multiple strategies to find products
            product_elements = []
            
            # Strategy 1: Find all product links directly (most reliable)
            try:
                product_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
                if product_links:
                    # Get parent containers of product links
                    seen_links = set()
                    for link in product_links[:max_results * 3]:  # Get more to filter
                        href = link.get_attribute('href')
                        if href and href not in seen_links and '/p/' in href:
                            seen_links.add(href)
                            # Get parent container (usually 2-3 levels up)
                            try:
                                parent = link.find_element(By.XPATH, './ancestor::div[contains(@class, "_1AtVbE") or contains(@class, "_13oc-S") or @data-id][1]')
                                if parent not in product_elements:
                                    product_elements.append(parent)
                            except:
                                # If no specific parent, use the link's immediate parent
                                try:
                                    parent = link.find_element(By.XPATH, './..')
                                    if parent not in product_elements:
                                        product_elements.append(parent)
                                except:
                                    # Last resort: use the link itself
                                    if link not in product_elements:
                                        product_elements.append(link)
                    self.logger.debug(f"Found {len(product_elements)} products via product links")
            except Exception as e:
                self.logger.debug(f"Strategy 1 (product links) failed: {str(e)}")
            
            # Strategy 2: Use container selectors (if Strategy 1 didn't work well)
            if len(product_elements) < max_results:
                selectors = [
                    'div[data-id]',  # Products with data-id
                    '._1AtVbE',      # Product container class
                    '._13oc-S',      # Grid container
                    'div[class*="_1AtVbE"]',
                    'div[class*="_13oc-S"]',
                    'div[class*="tUxRFH"]'  # Alternative container
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        # Filter valid products
                        valid_elements = [e for e in elements if self._is_valid_product(e)]
                        
                        # Add unique elements
                        for elem in valid_elements:
                            if elem not in product_elements:
                                product_elements.append(elem)
                        
                        if len(product_elements) >= max_results:
                            self.logger.debug(f"Found {len(product_elements)} products using selector: {selector}")
                            break
                    except Exception as e:
                        self.logger.debug(f"Selector {selector} failed: {str(e)}")
                        continue
            
            if not product_elements:
                self.logger.warning("No product elements found on Flipkart")
                # Try one more time with a simpler approach
                try:
                    all_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/p/"]')
                    if all_links:
                        self.logger.info(f"Found {len(all_links)} product links, but couldn't extract containers")
                except:
                    pass
                return results
            
            # Limit to max_results
            product_elements = product_elements[:max_results * 2]
            
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
                        self.logger.debug(f"Skipping product {idx+1} - no valid price found (Title: {title[:30]}...)")
                    
                except Exception as e:
                    self.logger.debug(f"Error extracting product {idx+1}: {str(e)}")
                    continue
            
            self.logger.info(f"Successfully extracted {len(results)} products from Flipkart")
            
        except Exception as e:
            self.logger.error(f"Error scraping Flipkart: {str(e)}", exc_info=True)
        
        return results
