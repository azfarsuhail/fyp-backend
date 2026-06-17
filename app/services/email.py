import os
from typing import Optional
from datetime import datetime
from resend import Emails
from dotenv import load_dotenv

load_dotenv()

# Configuration - Load from environment variables
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
# Default to production domain - override with APP_URL env var for local dev
APP_URL = os.getenv("APP_URL", "https://kneeoa.online")

if not RESEND_API_KEY:
    print("WARNING: RESEND_API_KEY not set! Email functionality will be disabled.")


def send_reset_password_email(email_to: str, token: str) -> bool:
    """
    Send password reset email to user.
    
    Args:
        email_to: Recipient's email address
        token: JWT token for password reset
        
    Returns:
        True if email sent successfully, False otherwise
    """
    if not RESEND_API_KEY:
        print(f"[Email Service] Skipping email to {email_to} - RESEND_API_KEY not configured")
        return False
    
    reset_link = f"{APP_URL}/reset-password?token={token}"
    
    email_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .content p {{
                color: #333;
                line-height: 1.6;
                margin: 20px 0;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 14px 30px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
                margin: 20px 0;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 20px 30px;
                text-align: center;
                color: #6c757d;
                font-size: 12px;
                border-top: 1px solid #dee2e6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔒 Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>We received a request to reset your password. If you made this request, please click the button below to set a new password:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Important:</strong> This link will expire in <strong>30 minutes</strong> for security reasons. If you don't reset your password within this time, you'll need to request a new reset link.
                </div>
                
                <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
                
                <p><strong>Security Tips:</strong></p>
                <ul style="color: #555;">
                    <li>Never share your password with anyone</li>
                    <li>Use a strong, unique password</li>
                    <li>Enable two-factor authentication if available</li>
                </ul>
            </div>
            <div class="footer">
                <p>&copy; {datetime.now().year} Knee OA Backend. All rights reserved.</p>
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        Emails.send({
            "from": "Knee OA Backend <onboarding@resend.dev>",
            "to": [email_to],
            "subject": "Password Reset Request",
            "html": email_html
        })
        print(f"[Email Service] Reset password email sent to {email_to}")
        return True
        
    except Exception as e:
        print(f"[Email Service] Failed to send reset email to {email_to}: {str(e)}")
        return False
