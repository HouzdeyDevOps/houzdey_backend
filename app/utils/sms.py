"""SMS utilities for sending OTP via Termii"""

import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_sms_otp(phone_number: str, otp: str):
    """Send SMS OTP using Termii Token API"""
    try:
        url = f"{settings.TERMII_BASE_URL}/api/sms/otp/send"
        
        payload = {
            "api_key": settings.TERMII_API_KEY,
            "message_type": "NUMERIC",
            "to": phone_number,
            "from": settings.TERMII_SENDER_ID,
            "channel": "generic",
            "pin_attempts": 3,
            "pin_time_to_live": 10,  # 10 minutes
            "pin_length": 6,
            "pin_placeholder": "< 1234 >",
            "message_text": "Your Houzdey verification code is < 1234 >. Valid for 10 minutes.",
            "pin_type": "NUMERIC"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"SMS OTP sent successfully to {phone_number}")
            print(f"✅ SMS OTP sent successfully to {phone_number}")
            
            return result
            
    except httpx.HTTPStatusError as e:
        error_msg = f"Termii SMS API error: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Failed to send SMS OTP: {str(e)}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        raise Exception(error_msg)