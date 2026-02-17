"""
ShopEasy Web Application
Flask API + frontend for price comparison.
"""
import os
import sys
import math

# Run from project root so config and imports work
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, request, jsonify, send_from_directory
from utils.logger import setup_logger
from main import ShopEasy

app = Flask(__name__, static_folder='static', static_url_path='')
logger = setup_logger('ShopEasy')


def _serialize(obj):
    """
    Convert numpy/pandas types to native Python for JSON.
    Crucially handles NaN/Inf which break standard JSON.
    """
    import numpy as np
    
    # Handle Null/NaN/Infinity first
    if isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or np.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
        
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    
    if isinstance(obj, np.ndarray):
        return [_serialize(x) for x in obj.tolist()]
    
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    
    if isinstance(obj, list):
        return [_serialize(x) for x in obj]
        
    return obj


def get_top_results(product_name: str, max_results: int = 5):
    """Run search and return top N results sorted by price (low to high)."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    shop = ShopEasy(config_path=config_path)
    try:
        all_results = shop.search_product(product_name, max_results=max_results)
        if not all_results:
            return [], 0
            
        df = shop.data_analyzer.create_dataframe(all_results)
        analysis = shop.data_analyzer.analyze_prices(df)
        best_deals = analysis.get('best_deals', [])
        
        out = []
        if best_deals:
            for d in best_deals[:max_results]:
                price = d.get("price")
                try:
                    # Clean price string if it's not already a number
                    if isinstance(price, str):
                        price = float(price.replace("₹", "").replace(",", "").strip())
                except Exception:
                    price = 0
                d["price"] = price
                out.append(_serialize(d))
        else:
            # Fallback sort if analyze_prices doesn't return best_deals
            def _price_extractor(x):
                try:
                    val = x.get("price")
                    if val is None: return float('inf')
                    return float(str(val).replace("₹", "").replace(",", "").strip())
                except Exception:
                    return float('inf')
            
            sorted_results = sorted(all_results, key=_price_extractor)
            out = [_serialize(d) for d in sorted_results[:max_results]]
            
        return out, len(all_results)
    finally:
        shop.cleanup()


@app.route('/')
def index():
    """Serve the main frontend page."""
    r = send_from_directory(app.static_folder, 'index.html')
    r.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    r.headers['Pragma'] = 'no-cache'
    return r


@app.route('/api/search', methods=['GET', 'POST'])
def search():
    """Search products and return top results."""
    if request.method == 'GET':
        query = request.args.get('q', '').strip()
        demo = request.args.get('demo', '').lower() in ('1', 'true', 'yes')
    else:
        data = request.get_json(silent=True) or {}
        query = (data.get('query') or data.get('q') or '').strip()
        demo = data.get('demo', False) is True

    if not query:
        return jsonify({'error': 'Missing search query'}), 400

    try:
        # Fetch max results from query params or JSON body
        json_data = request.get_json(silent=True) or {}
        max_results = int(request.args.get('max') or json_data.get('max', 5))
    except (TypeError, ValueError):
        max_results = 5
    
    max_results = max(1, min(max_results, 20))

    print(f">>> Search started for: {query!r} (demo={demo})", flush=True)

    if demo:
        fake = [
            {'title': f'{query} - Amazon Deal', 'price': 1999.0, 'platform': 'Amazon', 'url': 'https://www.amazon.in', 'rating': '4.2'},
            {'title': f'{query} - Flipkart Offer', 'price': 2199.0, 'platform': 'Flipkart', 'url': 'https://www.flipkart.com', 'rating': '4.0'},
            {'title': f'{query} - Croma Exclusive', 'price': 2499.0, 'platform': 'Croma', 'url': 'https://www.croma.com', 'rating': None},
        ][:max_results]
        return jsonify({
            'query': query,
            'total_found': len(fake),
            'top_results': fake,
            'count': len(fake),
        })

    try:
        results, total = get_top_results(query, max_results=max_results)
        print(f">>> Search finished for: {query!r} -> {len(results)} results", flush=True)
        
        payload = {
            'query': query,
            'total_found': total,
            'top_results': results,
            'count': len(results)
        }

        if len(results) == 0:
            payload['sample_fallback'] = True
            payload['top_results'] = [
                {'title': f'Search {query} on Amazon', 'price': 0, 'platform': 'Amazon', 'url': 'https://www.amazon.in/s?k=' + query.replace(' ', '+'), 'rating': None},
                {'title': f'Search {query} on Flipkart', 'price': 0, 'platform': 'Flipkart', 'url': 'https://www.flipkart.com/search?q=' + query.replace(' ', '%20'), 'rating': None}
            ][:max_results]
            payload['count'] = len(payload['top_results'])
            
        return jsonify(payload)
    except Exception as e:
        print(f">>> Search failed for: {query!r} - {e}", flush=True)
        logger.exception('Search failed')
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'service': 'ShopEasy'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)