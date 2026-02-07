"""
Smart Recommendation System for ShopEasy
A modular ranking component that evaluates products across multiple e-commerce platforms
based on overall value rather than just price.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
from copy import deepcopy


class RecommendationSystem:
    """
    Smart Recommendation System that computes product scores using weighted factors.
    
    Evaluates products based on:
    - Price (lower is better)
    - Rating (higher is better)
    - Number of reviews (higher is better)
    - Delivery time (lower is better)
    - Return policy (better policy = higher score)
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize the recommendation system.
        
        Args:
            weights: Dictionary of weights for each factor. Default weights sum to 1.0.
                    Keys: 'price', 'rating', 'reviews', 'delivery_time', 'return_policy'
        """
        self.logger = logging.getLogger('ShopEasy')
        
        # Default weights (can be overridden via config)
        default_weights = {
            'price': 0.35,           # Price is important
            'rating': 0.25,           # Rating matters
            'reviews': 0.15,          # More reviews = more trust
            'delivery_time': 0.15,   # Fast delivery is valued
            'return_policy': 0.10    # Return policy matters
        }
        
        if weights:
            # Normalize weights to sum to 1.0
            total = sum(weights.values())
            if total > 0:
                self.weights = {k: v / total for k, v in weights.items()}
            else:
                self.weights = default_weights
                self.logger.warning("Invalid weights provided, using defaults")
        else:
            self.weights = default_weights
        
        self.logger.debug(f"Recommendation system initialized with weights: {self.weights}")
    
    def validate_product(self, product: Dict) -> bool:
        """
        Validate if a product has minimum required data.
        
        Args:
            product: Product dictionary
            
        Returns:
            True if product is valid, False otherwise
        """
        # Must have at least title, price, and platform
        required_fields = ['title', 'price', 'platform']
        return all(field in product and product[field] is not None for field in required_fields) and \
               product.get('price', 0) > 0
    
    def filter_valid_products(self, products: List[Dict]) -> List[Dict]:
        """
        Filter products to only include valid ones.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            List of valid products
        """
        valid_products = [p for p in products if self.validate_product(p)]
        invalid_count = len(products) - len(valid_products)
        if invalid_count > 0:
            self.logger.debug(f"Filtered out {invalid_count} invalid products")
        return valid_products
    
    def normalize_price(self, prices: pd.Series, invert: bool = True) -> pd.Series:
        """
        Normalize price values to 0-1 scale.
        Lower prices get higher scores (inverted).
        
        Args:
            prices: Series of price values
            invert: If True, lower prices get higher scores
            
        Returns:
            Normalized price scores (0-1)
        """
        if prices.empty or prices.min() == prices.max():
            return pd.Series([1.0] * len(prices), index=prices.index)
        
        normalized = (prices.max() - prices) / (prices.max() - prices.min())
        return normalized if invert else 1 - normalized
    
    def normalize_rating(self, ratings: pd.Series, max_rating: float = 5.0) -> pd.Series:
        """
        Normalize rating values to 0-1 scale.
        Higher ratings get higher scores.
        
        Args:
            ratings: Series of rating values (may contain NaN)
            max_rating: Maximum possible rating (default 5.0)
            
        Returns:
            Normalized rating scores (0-1)
        """
        # Fill missing ratings with median or 0
        filled_ratings = ratings.fillna(ratings.median() if not ratings.isna().all() else 0)
        
        if filled_ratings.empty or filled_ratings.max() == 0:
            return pd.Series([0.0] * len(ratings), index=ratings.index)
        
        # Normalize to 0-1 scale
        normalized = filled_ratings / max_rating
        return normalized.clip(0, 1)
    
    def normalize_reviews(self, reviews: pd.Series) -> pd.Series:
        """
        Normalize number of reviews to 0-1 scale using log scale.
        More reviews get higher scores.
        
        Args:
            reviews: Series of review counts (may contain NaN)
            
        Returns:
            Normalized review scores (0-1)
        """
        # Fill missing reviews with 0
        filled_reviews = reviews.fillna(0)
        
        if filled_reviews.empty or filled_reviews.max() == 0:
            return pd.Series([0.0] * len(reviews), index=reviews.index)
        
        # Use log scale to handle wide ranges (e.g., 10 to 10000 reviews)
        # Add 1 to avoid log(0)
        log_reviews = np.log1p(filled_reviews)
        
        if log_reviews.max() == 0:
            return pd.Series([0.0] * len(reviews), index=reviews.index)
        
        normalized = log_reviews / log_reviews.max()
        return normalized.clip(0, 1)
    
    def normalize_delivery_time(self, delivery_times: pd.Series, max_days: float = 30.0) -> pd.Series:
        """
        Normalize delivery time to 0-1 scale.
        Faster delivery (lower days) gets higher scores.
        
        Args:
            delivery_times: Series of delivery times in days (may contain NaN)
            max_days: Maximum expected delivery time for normalization
            
        Returns:
            Normalized delivery time scores (0-1, inverted)
        """
        # Fill missing delivery times with max_days (worst case)
        filled_times = delivery_times.fillna(max_days)
        
        if filled_times.empty or filled_times.max() == 0:
            return pd.Series([1.0] * len(delivery_times), index=delivery_times.index)
        
        # Invert: lower delivery time = higher score
        normalized = 1 - (filled_times / max_days)
        return normalized.clip(0, 1)
    
    def normalize_return_policy(self, return_policies: pd.Series) -> pd.Series:
        """
        Normalize return policy scores to 0-1 scale.
        Better return policies get higher scores.
        
        Args:
            return_policies: Series of return policy scores (0-1 or 0-10 scale, may contain NaN)
            
        Returns:
            Normalized return policy scores (0-1)
        """
        # Fill missing return policies with 0 (worst case)
        filled_policies = return_policies.fillna(0)
        
        if filled_policies.empty or filled_policies.max() == 0:
            return pd.Series([0.0] * len(return_policies), index=return_policies.index)
        
        # If values are > 1, assume they're on 0-10 scale and normalize
        if filled_policies.max() > 1:
            normalized = filled_policies / 10.0
        else:
            normalized = filled_policies
        
        return normalized.clip(0, 1)
    
    def compute_scores(self, products: List[Dict]) -> pd.DataFrame:
        """
        Compute final scores for all products.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            DataFrame with products and their scores
        """
        if not products:
            return pd.DataFrame()
        
        # Filter valid products
        valid_products = self.filter_valid_products(products)
        
        if not valid_products:
            self.logger.warning("No valid products to score")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(valid_products)
        
        # Normalize each factor
        df['price_score'] = self.normalize_price(df['price'])
        df['rating_score'] = self.normalize_rating(df.get('rating', pd.Series([None] * len(df))))
        df['reviews_score'] = self.normalize_reviews(df.get('num_reviews', pd.Series([None] * len(df))))
        df['delivery_score'] = self.normalize_delivery_time(df.get('delivery_time', pd.Series([None] * len(df))))
        df['return_score'] = self.normalize_return_policy(df.get('return_policy_score', pd.Series([None] * len(df))))
        
        # Compute weighted final score
        df['final_score'] = (
            df['price_score'] * self.weights['price'] +
            df['rating_score'] * self.weights['rating'] +
            df['reviews_score'] * self.weights['reviews'] +
            df['delivery_score'] * self.weights['delivery_time'] +
            df['return_score'] * self.weights['return_policy']
        )
        
        # Round scores for readability
        df['final_score'] = df['final_score'].round(4)
        
        return df
    
    def rank_products(self, products: List[Dict]) -> List[Dict]:
        """
        Rank products by their final scores in descending order.
        
        Args:
            products: List of product dictionaries
            
        Returns:
            List of products sorted by final score (best first)
        """
        df = self.compute_scores(products)
        
        if df.empty:
            return []
        
        # Sort by final score (descending)
        df_sorted = df.sort_values('final_score', ascending=False)
        
        # Convert back to list of dictionaries
        ranked_products = df_sorted.to_dict('records')
        
        return ranked_products
    
    def annotate_top_results(self, ranked_products: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        Annotate top results with labels like "Best Value", "Cheapest", "Fastest Delivery".
        
        Args:
            ranked_products: List of ranked products (from rank_products)
            top_n: Number of top products to annotate
            
        Returns:
            List of products with annotations added
        """
        if not ranked_products:
            return []
        
        annotated = deepcopy(ranked_products)
        top_products = annotated[:top_n]
        
        if not top_products:
            return annotated
        
        # Find best in each category
        df_top = pd.DataFrame(top_products)
        
        # Best Value (highest final score)
        if 'final_score' in df_top.columns:
            best_value_idx = df_top['final_score'].idxmax()
            if best_value_idx < len(top_products):
                if 'labels' not in top_products[best_value_idx]:
                    top_products[best_value_idx]['labels'] = []
                top_products[best_value_idx]['labels'].append("Best Value")
        
        # Cheapest
        if 'price' in df_top.columns:
            cheapest_idx = df_top['price'].idxmin()
            if cheapest_idx < len(top_products):
                if 'labels' not in top_products[cheapest_idx]:
                    top_products[cheapest_idx]['labels'] = []
                if "Best Value" not in top_products[cheapest_idx].get('labels', []):
                    top_products[cheapest_idx]['labels'].append("Cheapest")
        
        # Highest Rated
        if 'rating' in df_top.columns and not df_top['rating'].isna().all():
            highest_rated_idx = df_top['rating'].idxmax()
            if highest_rated_idx < len(top_products) and not pd.isna(df_top.loc[highest_rated_idx, 'rating']):
                if 'labels' not in top_products[highest_rated_idx]:
                    top_products[highest_rated_idx]['labels'] = []
                if "Best Value" not in top_products[highest_rated_idx].get('labels', []):
                    top_products[highest_rated_idx]['labels'].append("Highest Rated")
        
        # Fastest Delivery
        if 'delivery_time' in df_top.columns and not df_top['delivery_time'].isna().all():
            fastest_idx = df_top['delivery_time'].idxmin()
            if fastest_idx < len(top_products) and not pd.isna(df_top.loc[fastest_idx, 'delivery_time']):
                if 'labels' not in top_products[fastest_idx]:
                    top_products[fastest_idx]['labels'] = []
                if "Best Value" not in top_products[fastest_idx].get('labels', []):
                    top_products[fastest_idx]['labels'].append("Fastest Delivery")
        
        # Most Reviewed
        if 'num_reviews' in df_top.columns and not df_top['num_reviews'].isna().all():
            most_reviewed_idx = df_top['num_reviews'].idxmax()
            if most_reviewed_idx < len(top_products) and not pd.isna(df_top.loc[most_reviewed_idx, 'num_reviews']):
                if 'labels' not in top_products[most_reviewed_idx]:
                    top_products[most_reviewed_idx]['labels'] = []
                if "Best Value" not in top_products[most_reviewed_idx].get('labels', []):
                    top_products[most_reviewed_idx]['labels'].append("Most Reviewed")
        
        # Update the annotated list
        annotated[:top_n] = top_products
        
        return annotated
    
    def get_recommendations(self, products: List[Dict], top_n: int = 10, 
                           annotate: bool = True) -> List[Dict]:
        """
        Get top product recommendations with annotations.
        
        Args:
            products: List of product dictionaries
            top_n: Number of top recommendations to return
            annotate: Whether to add labels to top results
            
        Returns:
            List of top recommended products
        """
        # Rank products
        ranked = self.rank_products(products)
        
        if not ranked:
            return []
        
        # Annotate if requested
        if annotate:
            ranked = self.annotate_top_results(ranked, top_n=min(top_n, len(ranked)))
        
        # Return top N
        return ranked[:top_n]
    
    def get_score_breakdown(self, product: Dict) -> Dict:
        """
        Get detailed score breakdown for a single product.
        
        Args:
            product: Product dictionary
            
        Returns:
            Dictionary with score breakdown
        """
        if not self.validate_product(product):
            return {'error': 'Invalid product'}
        
        df = self.compute_scores([product])
        
        if df.empty:
            return {'error': 'Could not compute scores'}
        
        row = df.iloc[0]
        
        return {
            'product': product.get('title', 'Unknown'),
            'final_score': float(row['final_score']),
            'breakdown': {
                'price_score': float(row['price_score']),
                'rating_score': float(row['rating_score']),
                'reviews_score': float(row['reviews_score']),
                'delivery_score': float(row['delivery_score']),
                'return_score': float(row['return_score'])
            },
            'weights': self.weights
        }
