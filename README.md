# 🛒 ShopEasy - Automated Price Comparison Tool

ShopEasy is an automated tool designed to compare product prices across multiple e-commerce platforms, empowering users to make smart purchasing decisions quickly and efficiently.

ShopEasy scrapes the web for product data, analyzes prices, and presents the best options at a glance.

💡 **This tool can save users up to 80% of the time usually spent on manual price checking!**

## ✨ Features

- **Real-Time Price Comparison**: Compares prices across various e-commerce websites like Amazon, eBay, Flipkart, Croma, and more
- **Automated Web Scraping**: Uses Selenium for efficient, browser-based web scraping
- **Data Analysis**: Utilizes Pandas to clean and analyze collected data for the best price evaluation
- **Time Efficient**: Reduces manual work, providing results in minutes
- **Email Notifications**: Sends email alerts when the price drops below a user-defined threshold
- **Colored Logging**: Enhanced logging with color-coded messages for better readability

## 📋 Prerequisites

- Python 3.8 or higher
- Google Chrome browser installed
- ChromeDriver (automatically managed by webdriver-manager)

## 🚀 Installation

1. **Clone the repository** (or navigate to the project directory):
```bash
cd shopeasy
```

2. **Create a virtual environment** (highly recommended):
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

3. **Upgrade pip** (recommended for Python 3.13+):
```bash
python -m pip install --upgrade pip
```

4. **Install dependencies**:
```bash
pip install -r requirements.txt
```

**Note for Python 3.13 users**: If you encounter build errors, ensure you're using a virtual environment and have upgraded pip. The requirements file uses flexible version constraints to automatically select compatible versions with pre-built wheels.

4. **Configure the application**:
   - Edit `config.json` to enable/disable scrapers and configure settings
   - For email notifications, create a `.env` file (see `.env.example`)

## ⚙️ Configuration

### config.json

Edit `config.json` to customize your settings:

```json
{
  "scrapers": {
    "amazon": {
      "enabled": true
    },
    "flipkart": {
      "enabled": true
    },
    "ebay": {
      "enabled": true
    },
    "croma": {
      "enabled": true
    }
  },
  "email": {
    "enabled": false,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "",
    "sender_password": ""
  },
  "settings": {
    "headless": false,
    "timeout": 30,
    "max_results_per_site": 5,
    "price_drop_threshold_percent": 10
  }
}
```

### Email Configuration (Optional)

For email notifications, create a `.env` file in the project root:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
```

**Note**: For Gmail, you'll need to use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

## 📖 Usage

### Basic Usage

Search for a product and compare prices:

```bash
python main.py "laptop"
```

### Advanced Usage

```bash
# Search with price threshold
python main.py "iPhone 15" --threshold 50000

# Send email notification
python main.py "laptop" --threshold 30000 --email user@example.com

# Limit results per site
python main.py "headphones" --max-results 10

# Use custom config file
python main.py "smartphone" --config custom_config.json
```

### Command Line Arguments

- `product` (required): Product name to search
- `--threshold`: Price threshold for alerts (in ₹)
- `--email`: Email address to send notifications
- `--config`: Path to config file (default: `config.json`)
- `--max-results`: Maximum results per site (overrides config)

## 📊 Example Output

```
============================================================
🚀 ShopEasy - Starting Price Comparison
============================================================
🔍 Searching for: laptop
📊 Max results per site: 5
🌐 Scraping Amazon...
✓ Found 5 products on Amazon
🌐 Scraping Flipkart...
✓ Found 5 products on Flipkart
🌐 Scraping eBay...
✓ Found 5 products on eBay
🌐 Scraping Croma...
✓ Found 5 products on Croma

📈 Analyzing results...

============================================================
SHOPEASY PRICE COMPARISON REPORT
============================================================

Total Products Found: 20
Platforms Searched: Amazon, Flipkart, eBay, Croma

🏆 BEST DEAL:
   Product: ASUS VivoBook 15 X515EA-EJ322WS | Intel Core i3...
   Price: ₹34990.00
   Platform: Flipkart
   URL: https://www.flipkart.com/...

💰 PRICE STATISTICS:
   Average Price: ₹42500.00
   Price Range: ₹34990.00 - ₹59999.00
   Price Difference: ₹25009.00

📊 TOP 5 BEST DEALS:
   1. Flipkart: ₹34990.00 - ASUS VivoBook 15 X515EA-EJ322WS...
   2. Amazon: ₹37999.00 - Lenovo IdeaPad 3 Intel Core i3...
   3. Flipkart: ₹38990.00 - HP 15s Intel Core i3 11th Gen...
   4. Amazon: ₹39999.00 - Acer Aspire 3 Intel Core i3...
   5. Croma: ₹42990.00 - Dell Inspiron 15 3511 Intel Core i3...

============================================================
```

## 🏗️ Project Structure

```
shopeasy/
├── main.py                 # Main application entry point
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .env.example           # Email configuration template
├── scrapers/              # Web scrapers for different platforms
│   ├── __init__.py
│   ├── base_scraper.py    # Base scraper class
│   ├── amazon_scraper.py  # Amazon scraper
│   ├── flipkart_scraper.py # Flipkart scraper
│   ├── ebay_scraper.py    # eBay scraper
│   └── croma_scraper.py   # Croma scraper
└── utils/                 # Utility modules
    ├── __init__.py
    ├── logger.py          # Colored logging utility
    ├── data_analyzer.py   # Data analysis with Pandas
    └── email_notifier.py  # Email notification system
```

## 🔧 How It Works

1. **Product Search**: The tool searches for the specified product across all enabled e-commerce platforms simultaneously
2. **Web Scraping**: Uses Selenium WebDriver to scrape product information (title, price, URL, rating)
3. **Data Collection**: Collects all results into a structured format
4. **Data Analysis**: Uses Pandas to analyze prices, find the best deals, and generate statistics
5. **Report Generation**: Creates a comprehensive report showing:
   - Best deal found
   - Price statistics (average, range, difference)
   - Top 5 best deals
   - Platform comparison
6. **Notifications**: Sends email alerts if price drops below threshold (optional)

## ⚠️ Important Notes

- **Web Scraping Ethics**: This tool is for personal use and educational purposes. Always respect websites' Terms of Service and robots.txt files
- **Rate Limiting**: The tool includes delays between requests to avoid overwhelming servers
- **Website Changes**: E-commerce websites frequently update their HTML structure. If a scraper stops working, you may need to update the CSS selectors
- **Legal Compliance**: Ensure you comply with local laws and website terms when using web scraping tools

## 🐛 Troubleshooting

### Installation Issues

**Problem**: `pip install -r requirements.txt` fails with build errors (especially on Python 3.13+)

**Solutions**:
1. **Use a virtual environment** (most important):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

2. **Upgrade pip first**:
   ```bash
   python -m pip install --upgrade pip
   ```

3. **If still failing**, try installing packages individually to identify the problematic one:
   ```bash
   pip install selenium webdriver-manager colorama python-dotenv beautifulsoup4 requests lxml
   pip install pandas
   ```

4. **For Python 3.13+**: If pandas installation fails, you may need to wait for pre-built wheels or use Python 3.11/3.12 instead.

5. **GCC/Build Tools Error**: If you see "NumPy requires GCC >= 8.4", you're trying to build from source. Use a virtual environment and ensure pip can find pre-built wheels, or consider using Python 3.11/3.12 which have better package support.

### ChromeDriver Issues
If you encounter ChromeDriver errors, ensure Chrome browser is installed and up to date. The tool automatically manages ChromeDriver via webdriver-manager.

### Scraper Not Working
If a specific scraper fails:
1. Check if the website is accessible
2. Verify the website hasn't changed its HTML structure
3. Try running with `headless: false` in config.json to see what's happening
4. Check the logs for specific error messages

### Email Not Sending
1. Verify your email credentials in `.env` or `config.json`
2. For Gmail, ensure you're using an App Password, not your regular password
3. Check if your email provider requires specific SMTP settings
4. Verify firewall/antivirus isn't blocking SMTP connections

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Add support for more e-commerce platforms
- Improve existing scrapers
- Enhance data analysis features
- Fix bugs and improve error handling

## 📝 License

This project is provided as-is for educational and personal use.

## 🙏 Acknowledgments

- Built with [Selenium](https://www.selenium.dev/) for web automation
- Data analysis powered by [Pandas](https://pandas.pydata.org/)
- Colored logging with [Colorama](https://pypi.org/project/colorama/)

## 📧 Support

For issues, questions, or suggestions, please open an issue on the repository.

---

**Happy Shopping! 🛒✨**
