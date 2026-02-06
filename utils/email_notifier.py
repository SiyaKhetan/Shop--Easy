"""
Email notification module for price alerts
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
import logging
import os
from dotenv import load_dotenv

load_dotenv()


class EmailNotifier:
    """Send email notifications for price drops"""
    
    def __init__(self, smtp_server: str = None, smtp_port: int = None, 
                 sender_email: str = None, sender_password: str = None):
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = sender_email or os.getenv('EMAIL_SENDER', '')
        self.sender_password = sender_password or os.getenv('EMAIL_PASSWORD', '')
        self.logger = logging.getLogger('ShopEasy')
    
    def is_configured(self) -> bool:
        """Check if email is configured"""
        return bool(self.sender_email and self.sender_password)
    
    def send_price_alert(self, recipient: str, product_name: str, 
                        best_deal: Dict, threshold_price: float = None):
        """Send email alert for price drop"""
        if not self.is_configured():
            self.logger.warning("Email not configured. Skipping notification.")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = f"💰 Price Alert: {product_name}"
            
            body = f"""
            <html>
            <body>
                <h2>Price Alert: {product_name}</h2>
                <p>Great news! We found a great deal for you:</p>
                <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px;">
                    <h3>🏆 Best Deal Found:</h3>
                    <p><strong>Product:</strong> {best_deal['title']}</p>
                    <p><strong>Price:</strong> ₹{best_deal['price']:.2f}</p>
                    <p><strong>Platform:</strong> {best_deal['platform']}</p>
                    <p><strong>URL:</strong> <a href="{best_deal['url']}">{best_deal['url']}</a></p>
                </div>
                {"<p><strong>Price below threshold:</strong> ₹" + str(threshold_price) + "</p>" if threshold_price else ""}
                <p>Happy Shopping! 🛒</p>
                <hr>
                <p><small>This email was sent by ShopEasy - Your Smart Price Comparison Tool</small></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"Price alert email sent to {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_comparison_report(self, recipient: str, product_name: str, 
                              report_text: str, analysis: Dict):
        """Send comparison report via email"""
        if not self.is_configured():
            self.logger.warning("Email not configured. Skipping notification.")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = f"ShopEasy Report: {product_name}"
            
            body = f"""
            <html>
            <body>
                <h2>ShopEasy Price Comparison Report</h2>
                <p><strong>Product Searched:</strong> {product_name}</p>
                <pre style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; font-family: monospace;">
{report_text}
                </pre>
                <p>Happy Shopping! 🛒</p>
                <hr>
                <p><small>This email was sent by ShopEasy - Your Smart Price Comparison Tool</small></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"Comparison report sent to {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False
