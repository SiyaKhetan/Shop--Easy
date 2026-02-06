"""
Data analysis module using Pandas
"""
import pandas as pd
from typing import List, Dict
import logging


class DataAnalyzer:
    """Analyze and process product data"""
    
    def __init__(self):
        self.logger = logging.getLogger('ShopEasy')
    
    def create_dataframe(self, all_results: List[Dict]) -> pd.DataFrame:
        """Create pandas DataFrame from scraped results"""
        if not all_results:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_results)
        return df
    
    def analyze_prices(self, df: pd.DataFrame) -> Dict:
        """Analyze prices and find best deals"""
        if df.empty or 'price' not in df.columns:
            return {
                'total_results': 0,
                'platforms': [],
                'cheapest': None,
                'average_price': None,
                'price_range': None,
                'best_deals': []
            }
        
        # Filter out products with invalid prices (but keep for reporting)
        valid_df = df[df['price'] > 0].copy()
        
        # If no valid prices, still return info about what was found
        if valid_df.empty:
            return {
                'total_results': len(df),
                'platforms': df['platform'].unique().tolist() if 'platform' in df.columns else [],
                'cheapest': None,
                'average_price': None,
                'price_range': None,
                'best_deals': [],
                'products_without_price': len(df[df['price'] == 0]) if 'price' in df.columns else 0
            }
        
        analysis = {
            'total_results': len(valid_df),
            'platforms': valid_df['platform'].unique().tolist() if 'platform' in valid_df.columns else [],
            'cheapest': None,
            'average_price': None,
            'price_range': None,
            'best_deals': []
        }
        
        # Find cheapest product
        cheapest_idx = valid_df['price'].idxmin()
        analysis['cheapest'] = valid_df.loc[cheapest_idx].to_dict()
        
        # Calculate average price
        analysis['average_price'] = valid_df['price'].mean()
        
        # Price range
        analysis['price_range'] = {
            'min': valid_df['price'].min(),
            'max': valid_df['price'].max(),
            'difference': valid_df['price'].max() - valid_df['price'].min()
        }
        
        # Top 5 best deals (lowest prices)
        top_deals = valid_df.nsmallest(min(5, len(valid_df)), 'price')
        analysis['best_deals'] = top_deals.to_dict('records')
        
        return analysis
    
    def compare_platforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compare average prices across platforms"""
        if df.empty:
            return pd.DataFrame()
        
        platform_stats = df.groupby('platform').agg({
            'price': ['mean', 'min', 'max', 'count']
        }).round(2)
        
        platform_stats.columns = ['avg_price', 'min_price', 'max_price', 'count']
        platform_stats = platform_stats.sort_values('avg_price')
        
        return platform_stats
    
    def filter_by_price_range(self, df: pd.DataFrame, min_price: float = None, max_price: float = None) -> pd.DataFrame:
        """Filter products by price range"""
        filtered_df = df.copy()
        
        if min_price is not None:
            filtered_df = filtered_df[filtered_df['price'] >= min_price]
        
        if max_price is not None:
            filtered_df = filtered_df[filtered_df['price'] <= max_price]
        
        return filtered_df
    
    def sort_by_price(self, df: pd.DataFrame, ascending: bool = True) -> pd.DataFrame:
        """Sort products by price"""
        return df.sort_values('price', ascending=ascending)
    
    def get_summary_report(self, df: pd.DataFrame) -> str:
        """Generate a text summary report"""
        if df.empty:
            return "No products found."
        
        analysis = self.analyze_prices(df)
        report = []
        
        report.append("=" * 60)
        report.append("SHOPEASY PRICE COMPARISON REPORT")
        report.append("=" * 60)
        report.append(f"\nTotal Products Found: {analysis['total_results']}")
        report.append(f"Platforms Searched: {', '.join(analysis['platforms'])}")
        
        if analysis['cheapest']:
            cheapest = analysis['cheapest']
            report.append(f"\n🏆 BEST DEAL:")
            report.append(f"   Product: {cheapest['title'][:60]}...")
            report.append(f"   Price: ₹{cheapest['price']:.2f}")
            report.append(f"   Platform: {cheapest['platform']}")
            report.append(f"   URL: {cheapest['url']}")
        
        report.append(f"\n💰 PRICE STATISTICS:")
        report.append(f"   Average Price: ₹{analysis['average_price']:.2f}")
        if analysis['price_range']:
            report.append(f"   Price Range: ₹{analysis['price_range']['min']:.2f} - ₹{analysis['price_range']['max']:.2f}")
            report.append(f"   Price Difference: ₹{analysis['price_range']['difference']:.2f}")
        
        report.append(f"\n📊 TOP 5 BEST DEALS:")
        for i, deal in enumerate(analysis['best_deals'][:5], 1):
            report.append(f"   {i}. {deal['platform']}: ₹{deal['price']:.2f} - {deal['title'][:50]}...")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
