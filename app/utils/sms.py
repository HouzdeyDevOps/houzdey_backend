"""SMS utilities: send OTP codes through Brevo, falling back to Termii."""

import asyncio
import logging
import re

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BREVO_API = "https://api.brevo.com/v3"
# Brevo accepts a send (201) and reports a failed delivery afterwards as one of these events.
BREVO_FAILED_EVENTS = {"rejected", "blocked", "hardBounces", "softBounces", "skipped"}


def normalize_phone(phone_number: str) -> str:
    """Digits only with country code. A Nigerian local number (0705...) becomes 234705...."""
    digits = re.sub(r"\D", "", phone_number)
    if digits.startswith("0") and len(digits) == 11:
        return "234" + digits[1:]
    return digits


def otp_message(otp: str) -> str:
    return f"Your Houzdey verification code is {otp}. Valid for 10 minutes."


async def _brevo_rejected(client: httpx.AsyncClient, phone: str, message_id: str) -> bool:
    """Poll Brevo's event log for a few seconds; True if it reports the message as failed."""
    waited = 0
    while waited < settings.BREVO_SMS_VERIFY_SECONDS:
        await asyncio.sleep(2)
        waited += 2
        response = await client.get(
            f"{BREVO_API}/transactionalSMS/statistics/events",
            params={"phoneNumber": phone, "limit": 10, "sort": "desc"},
            headers={"api-key": settings.BREVO_API_KEY, "accept": "application/json"},
        )
        if response.status_code != 200:
            return False
        for event in response.json().get("events", []):
            if str(event.get("messageId")) == message_id and event.get("event") in BREVO_FAILED_EVENTS:
                logger.warning("Brevo reported SMS %s as %s: %s", message_id, event["event"], event.get("reason"))
                return True
    return False


async def send_via_brevo(phone_number: str, otp: str) -> None:
    if not settings.BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is not set")
    phone = normalize_phone(phone_number)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BREVO_API}/transactionalSMS/send",
            headers={"api-key": settings.BREVO_API_KEY, "accept": "application/json"},
            json={
                "sender": settings.BREVO_SMS_SENDER,
                "recipient": phone,
                "content": otp_message(otp),
                "type": "transactional",
                "tag": "phone_otp",
            },
        )
        response.raise_for_status()
        message_id = str(response.json().get("messageId", ""))
        if message_id and settings.BREVO_SMS_VERIFY_SECONDS > 0 and await _brevo_rejected(client, phone, message_id):
            raise RuntimeError("Brevo rejected the SMS")


async def send_via_termii(phone_number: str, otp: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.TERMII_BASE_URL}/api/sms/send",
            json={
                "api_key": settings.TERMII_API_KEY,
                "to": normalize_phone(phone_number),
                "from": settings.TERMII_SENDER_ID,
                "sms": otp_message(otp),
                "type": "plain",
                "channel": "generic",
            },
        )
        response.raise_for_status()


PROVIDERS = {"brevo": send_via_brevo, "termii": send_via_termii}


async def send_sms_otp(phone_number: str, otp: str) -> str:
    """Send the OTP with the first provider in SMS_PROVIDERS that works; returns that provider's name."""
    order = [name.strip().lower() for name in settings.SMS_PROVIDERS.split(",") if name.strip()]
    errors = []
    for name in order:
        sender = PROVIDERS.get(name)
        if sender is None:
            logger.error("Unknown SMS provider %r in SMS_PROVIDERS", name)
            continue
        try:
            await sender(phone_number, otp)
            logger.info("SMS OTP sent via %s", name)
            return name
        except Exception as e:
            detail = e.response.text[:200] if isinstance(e, httpx.HTTPStatusError) else str(e)
            logger.error("SMS provider %s failed: %s", name, detail)
            errors.append(f"{name}: {detail}")
    raise Exception("Failed to send SMS OTP. " + "; ".join(errors))
