"""
ShopEasy - Automated Price Comparison Tool
Main application orchestrator (Updated for Myntra & Amazon Fix)
"""
import json
import argparse
import sys
from typing import List, Dict
from utils.logger import setup_logger
from utils.data_analyzer import DataAnalyzer
from utils.email_notifier import EmailNotifier
from utils.recommendation_system import RecommendationSystem

# Import Scrapers
from scrapers.amazon_scraper import AmazonScraper
from scrapers.flipkart_scraper import FlipkartScraper
from scrapers.myntra_scraper import MyntraScraper  # Added Myntra
from scrapers.croma_scraper import CromaScraper

class ShopEasy:
    """Main ShopEasy application"""
    
    def __init__(self, config_path: str = 'config.json'):
        self.logger = setup_logger('ShopEasy')
        self.config = self.load_config(config_path)
        
        # Initialize recommendation system if enabled
        recommendation_system = None
        rec_config = self.config.get('recommendation_system', {})
        if rec_config.get('enabled', True):
            weights = rec_config.get('weights', {})
            recommendation_system = RecommendationSystem(weights=weights)
            self.logger.info("✓ Smart Recommendation System initialized")
        
        self.data_analyzer = DataAnalyzer(recommendation_system=recommendation_system)
        self.email_notifier = EmailNotifier(
            smtp_server=self.config.get('email', {}).get('smtp_server'),
            smtp_port=self.config.get('email', {}).get('smtp_port'),
            sender_email=self.config.get('email', {}).get('sender_email'),
            sender_password=self.config.get('email', {}).get('sender_password')
        )
        self.scrapers = []
        self.setup_scrapers()
    
    def load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Config file not found: {config_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in config file: {config_path}")
            sys.exit(1)
    
    def setup_scrapers(self):
        """Initialize enabled scrapers"""
        scrapers_config = self.config.get('scrapers', {})
        settings = self.config.get('settings', {})
        headless = settings.get('headless', False)
        timeout = settings.get('timeout', 30)
        
        # Updated: Replaced 'ebay' with 'myntra'
        scraper_classes = {
            'amazon': AmazonScraper,
            'flipkart': FlipkartScraper,
            'myntra': MyntraScraper,
            'croma': CromaScraper
        }
        
        for platform, scraper_class in scraper_classes.items():
            if scrapers_config.get(platform, {}).get('enabled', False):
                try:
                    scraper = scraper_class(headless=headless, timeout=timeout)
                    self.scrapers.append(scraper)
                    self.logger.info(f"✓ {platform.capitalize()} scraper initialized")
                except Exception as e:
                    self.logger.error(f"✗ Failed to initialize {platform} scraper: {str(e)}")
    
    def search_product(self, product_name: str, max_results: int = None) -> List[Dict]:
        """Search for product across all enabled platforms"""
        if not self.scrapers:
            self.logger.error("No scrapers available!")
            return []
        
        max_results = max_results or self.config.get('settings', {}).get('max_results_per_site', 5)
        all_results = []
        
        self.logger.info(f"🔍 Searching for: {product_name}")
        
        for scraper in self.scrapers:
            try:
                self.logger.info(f"🌐 Scraping {scraper.platform}...")
                results = scraper.search_product(product_name, max_results)
                all_results.extend(results)
                self.logger.info(f"✓ Found {len(results)} products on {scraper.platform}")
            except Exception as e:
                self.logger.error(f"✗ Error scraping {scraper.platform}: {str(e)}")
            # Note: We do NOT close the scraper here if we want to keep the session alive, 
            # but usually, we close at the very end of the app lifecycle.
        
        return all_results
    
    def compare_prices(self, product_name: str, threshold_price: float = None, 
                       send_email: bool = False, recipient: str = None):
        """Main method to compare prices"""
        self.logger.info("=" * 60)
        self.logger.info("🚀 ShopEasy - Starting Price Comparison")
        self.logger.info("=" * 60)
        
        # Search products
        all_results = self.search_product(product_name)
        
        if not all_results:
            self.logger.warning("⚠️  No products found! Try checking your internet or updating selectors.")
            return
        
        # Analysis
        self.logger.info("\n📈 Analyzing results...")
        df = self.data_analyzer.create_dataframe(all_results)
        analysis = self.data_analyzer.analyze_prices(df)
        
        # Generate and print report
        report = self.data_analyzer.get_summary_report(df)
        print("\n" + report)
        
        # Price Drop Logic
        if threshold_price and analysis.get('cheapest'):
            best_price = analysis['cheapest']['price']
            if best_price <= threshold_price:
                self.logger.info(f"🎉 Price below threshold! (₹{best_price:.2f} <= ₹{threshold_price:.2f})")
                if send_email and recipient:
                    self.email_notifier.send_price_alert(recipient, product_name, analysis['cheapest'], threshold_price)
        
        # Platform Stats
        self.logger.info("\n📊 Platform Comparison:")
        platform_stats = self.data_analyzer.compare_platforms(df)
        print("\n" + platform_stats.to_string())
        
        self.logger.info("\n✅ Price comparison completed!")
    
    def cleanup(self):
        """Cleanup resources"""
        for scraper in self.scrapers:
            try:
                scraper.close()
            except:
                pass

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='ShopEasy - Automated Price Comparison Tool')
    parser.add_argument('product', help='Product name to search')
    parser.add_argument('--threshold', type=float, help='Price threshold for alerts')
    parser.add_argument('--email', help='Email address to send notifications')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        import logging
        logging.getLogger('ShopEasy').setLevel(logging.DEBUG)
    
    app = ShopEasy(config_path=args.config)
    
    try:
        app.compare_prices(
            product_name=args.product,
            threshold_price=args.threshold,
            send_email=bool(args.email),
            recipient=args.email
        )
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        app.cleanup()

if __name__ == '__main__':
    main()