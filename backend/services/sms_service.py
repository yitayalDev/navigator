"""
SMS Service Module
Handles SMS sending for password reset functionality using Twilio
"""
import os
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class SMSService:
    """SMS service for sending verification codes using Twilio."""
    
    def __init__(self):
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.enabled = all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_phone_number])
        
        if self.enabled:
            try:
                from twilio.rest import Client
                self.client = Client(self.twilio_account_sid, self.twilio_auth_token)
                logger.info("Twilio SMS service initialized successfully")
            except ImportError:
                logger.error("Twilio library not installed. Run: pip install twilio")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                self.enabled = False
        else:
            logger.warning("Twilio credentials not configured in .env file")
    
    def send_sms(self, to_phone: str, message: str) -> bool:
        """Send SMS to the specified phone number."""
        if not self.enabled:
            logger.error("SMS service is not enabled. Please configure Twilio credentials.")
            return False
        
        try:
            # Format phone number (ensure it starts with +)
            if not to_phone.startswith('+'):
                to_phone = '+' + to_phone
            
            message = self.client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=to_phone
            )
            logger.info(f"SMS sent successfully to {to_phone}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {e}")
            return False
    
    def generate_verification_code(self) -> str:
        """Generate a 6-digit verification code."""
        return str(random.randint(100000, 999999))
    
    def send_verification_code(self, to_phone: str, code: str, username: str) -> bool:
        """Send verification code via SMS."""
        message = f"""UOG Navigator Admin Password Reset

Your verification code is: {code}

This code expires in 10 minutes.

If you did not request this, please ignore this message.

Requested by: {username}
"""
        return self.send_sms(to_phone, message)


# Global SMS service instance
sms_service = SMSService()


# In-memory storage for verification codes (for demo purposes)
# In production, use Redis or database
verification_codes = {}  # {code: {'username': ..., 'phone': ..., 'expires': ...}}


def store_verification_code(code: str, username: str, phone: str):
    """Store verification code with expiration time (10 minutes)."""
    verification_codes[code] = {
        'username': username,
        'phone': phone,
        'expires': datetime.now() + timedelta(minutes=10)
    }


def verify_code(code: str, username: str) -> bool:
    """Verify if code is valid and not expired."""
    if code not in verification_codes:
        return False
    
    entry = verification_codes[code]
    if entry['username'] != username:
        return False
    
    if datetime.now() > entry['expires']:
        # Code expired, remove it
        del verification_codes[code]
        return False
    
    return True


def consume_verification_code(code: str):
    """Remove verification code after successful use."""
    if code in verification_codes:
        del verification_codes[code]


def get_user_phone(username: str, db) -> str:
    """Get user's phone number from database."""
    try:
        user = db.get_admin_user(username)
        if user:
            return user.get('phone', '')
        return ''
    except:
        return ''


def send_password_reset_sms(username: str, phone: str, db) -> dict:
    """Send password reset SMS to user."""
    if not phone:
        return {'success': False, 'message': 'No phone number associated with this account'}
    
    if not sms_service.enabled:
        return {'success': False, 'message': 'SMS service is not configured'}
    
    # Generate and store code
    code = sms_service.generate_verification_code()
    store_verification_code(code, username, phone)
    
    # Send SMS
    if sms_service.send_verification_code(phone, code, username):
        return {'success': True, 'message': f'SMS sent to {phone[-4:].rjust(len(phone), "*")}'}
    else:
        return {'success': False, 'message': 'Failed to send SMS'}