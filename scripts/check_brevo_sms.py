"""Smoke-test Brevo transactional SMS.

Needs a Brevo API key (the "xkeysib-..." key from SMTP & API -> API keys, NOT the SMTP key) in .env:

    BREVO_API_KEY=xkeysib-...
    BREVO_SMS_SENDER=Houzdey        # optional; max 11 letters/digits, or 15 digits for a number

Run from the backend folder:

    python scripts/check_brevo_sms.py                          # shows your account and SMS credits, sends nothing
    python scripts/check_brevo_sms.py --to +2347054675026      # also sends one test SMS (uses a paid credit)
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API = "https://api.brevo.com/v3"


def call(method: str, path: str, api_key: str, body: dict = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{API}{path}", data=data, method=method,
        headers={"api-key": api_key, "accept": "application/json", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"message": raw[:300]}
    except urllib.error.URLError as e:
        return 0, {"message": str(e.reason)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--to", help="phone number in international format, e.g. +2347054675026")
    parser.add_argument("--message", default="Houzdey test: your Brevo SMS is working.")
    args = parser.parse_args()

    api_key = os.environ.get("BREVO_API_KEY", "")
    sender = os.environ.get("BREVO_SMS_SENDER", "Houzdey")
    if not api_key:
        print("[FAIL] BREVO_API_KEY is not set in .env (create an API key in Brevo: SMTP & API -> API keys)")
        sys.exit(1)
    if api_key.startswith("xsmtpsib-"):
        print("[FAIL] that is an SMTP key. SMS needs an API key that starts with xkeysib-")
        sys.exit(1)

    print("Account")
    status, account = call("GET", "/account", api_key)
    if status != 200:
        print(f"  [FAIL] {status}: {account.get('message')}")
        sys.exit(1)
    print(f"  [ok] API key accepted for {account.get('email')}")
    for plan in account.get("plan", []):
        if "sms" in str(plan.get("type", "")).lower():
            print(f"  SMS credits: {plan.get('credits')}")

    if not args.to:
        print("\nAccount check passed. Add --to <number> to send a test SMS.")
        return

    phone = args.to.lstrip("+")
    if not re.fullmatch(r"\d{8,15}", phone):
        print(f"  [FAIL] {args.to!r} is not an international number like +2347054675026")
        sys.exit(1)

    print(f"\nSending SMS from '{sender}' to +{phone}")
    status, result = call("POST", "/transactionalSMS/sms", api_key, {
        "sender": sender, "recipient": phone, "content": args.message, "type": "transactional",
    })
    if status in (200, 201):
        print(f"  [ok] Brevo accepted it: {json.dumps(result)}")
        print("  Accepted is not delivered: check the phone, and Brevo's SMS logs if it does not arrive.")
        return
    print(f"  [FAIL] {status}: {result.get('code', '')} {result.get('message', result)}")
    sys.exit(1)


if __name__ == "__main__":
    main()
