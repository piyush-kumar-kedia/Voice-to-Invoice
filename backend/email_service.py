"""Email service for sending invoices"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import logging

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', SMTP_USERNAME)
SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'VoiceBill')

def send_invoice_email(
    to_email: str,
    customer_name: str,
    invoice_number: str,
    total_amount: float,
    pdf_content: bytes,
    payment_link: str = None,
    language: str = 'en'
):
    """Send invoice email with PDF attachment"""
    try:
        # Email subject
        subject = f"Invoice {invoice_number} from VoiceBill" if language == 'en' else f"\u091a\u093e\u0932\u093e\u0928 {invoice_number} - VoiceBill"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Email body HTML
        payment_btn_hi = f"<p><a href='{payment_link}' style='background: #00897b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;'>अभी भुगतान करें</a></p>" if payment_link else ""
        payment_btn_en = f"<p><a href='{payment_link}' style='background: #00897b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;'>Pay Now</a></p>" if payment_link else ""
        
        if language == 'hi':
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #00897b;">VoiceBill</h2>
                <p>प्रिय {customer_name},</p>
                <p>आपका चालान संलग्न है।</p>
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>चालान संख्या:</strong> {invoice_number}</p>
                    <p><strong>कुल राशि:</strong> ₹{total_amount:.2f}</p>
                </div>
                {payment_btn_hi}
                <p>धन्यवाद!<br>VoiceBill Team</p>
            </body>
            </html>
            """
        else:
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #00897b;">VoiceBill</h2>
                <p>Dear {customer_name},</p>
                <p>Please find your invoice attached.</p>
                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Invoice Number:</strong> {invoice_number}</p>
                    <p><strong>Total Amount:</strong> Rs. {total_amount:.2f}</p>
                </div>
                {payment_btn_en}
                <p>Thank you for your business!<br>VoiceBill Team</p>
            </body>
            </html>
            """
        
        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))
        
        # Attach PDF
        pdf_attachment = MIMEApplication(pdf_content, _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f'invoice_{invoice_number}.pdf')
        msg.attach(pdf_attachment)
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Invoice email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False
