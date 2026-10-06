"""Smoke-test the Brevo SMTP credentials.

Run from the backend folder (uses the BREVO_* values in .env):

    python scripts/check_smtp.py                    # connect + log in only, sends nothing
    python scripts/check_smtp.py --to you@mail.com  # also send a test email through the app's send_email()
"""
import argparse
import asyncio
import os
import smtplib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# send_email() prints emoji; make that safe on Windows consoles that default to cp1252.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

# Load .env first: real environment variables beat the .env file, so the placeholders below
# must only fill in settings that .env does not define.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Only the email settings matter here; fill the app's other required settings so Settings() loads.
for _name in (
    "SECRET_KEY", "MONGO_URL", "CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET",
    "CLOUDINARY_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI", "TERMII_API_KEY",
):
    os.environ.setdefault(_name, "unused")
PLACEHOLDER_SENDER = "unset@example.invalid"
os.environ.setdefault("EMAIL_FROM", PLACEHOLDER_SENDER)

from app.core.config import settings  # noqa: E402
from app.utils.email import send_email  # noqa: E402

SERVER, PORT = "smtp-relay.brevo.com", 587


def check_login() -> bool:
    print(f"Connecting to {SERVER}:{PORT}")
    try:
        with smtplib.SMTP(SERVER, PORT, timeout=20) as server:
            server.starttls()
            print("  [ok] connected and STARTTLS accepted")
            server.login(settings.BREVO_SMTP_USERNAME, settings.BREVO_SMTP_PASSWORD)
            print("  [ok] login accepted")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"  [FAIL] login rejected: {e.smtp_code} {e.smtp_error!r} (check BREVO_SMTP_USERNAME / the SMTP key)")
    except (OSError, smtplib.SMTPException) as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")
    return False


async def check_send(to: str) -> bool:
    if settings.EMAIL_FROM == PLACEHOLDER_SENDER:
        print("  [FAIL] EMAIL_FROM is not set in .env; set it to your Brevo-verified sender address")
        return False
    print(f"Sending a test email from {settings.EMAIL_FROM} to {to}")
    try:
        await send_email(to, "Houzdey SMTP test", "<p>This is a test email from the Houzdey backend.</p>")
        print("  [ok] Brevo accepted the message (check the inbox and spam folder)")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        print("  Brevo rejects senders that are not verified: EMAIL_FROM must be a validated sender or domain.")
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--to", help="send a test email to this address")
    args = parser.parse_args()
    ok = check_login()
    if ok and args.to:
        ok = asyncio.run(check_send(args.to))
    print("\nAll checks passed" if ok else "\nFAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
