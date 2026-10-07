"""Check whether old Cloudinary files can still be fetched, and why delivery is blocked.

Needs CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET in .env.

    python scripts/check_cloudinary_access.py                 # uses a real listing's image from the live API
    python scripts/check_cloudinary_access.py --url <image url>
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import cloudinary  # noqa: E402
import cloudinary.api  # noqa: E402
import cloudinary.utils  # noqa: E402

API = "https://api.houzdey.com/api/v1/properties"


def http_status(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "houzdey-cloudinary-check"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return f"{response.status} ({response.headers.get('Content-Type')}, {len(response.read())} bytes)"
    except urllib.error.HTTPError as e:
        return f"{e.code} {e.headers.get('X-Cld-Error', '')}".strip()
    except urllib.error.URLError as e:
        return f"failed: {e.reason}"


def sample_url() -> str:
    request = urllib.request.Request(f"{API}?limit=50&page=3&sort_by=created_at&sort_order=desc",
                                     headers={"User-Agent": "houzdey-cloudinary-check"})
    with urllib.request.urlopen(request, timeout=30) as response:
        for prop in json.load(response)["properties"]:
            for url in prop["images"]:
                if "res.cloudinary.com" in url:
                    return url
    sys.exit("No Cloudinary image found in the live API")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url")
    args = parser.parse_args()

    missing = [n for n in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET") if not os.environ.get(n)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)}")
    cloudinary.config(cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"], api_key=os.environ["CLOUDINARY_API_KEY"],
                      api_secret=os.environ["CLOUDINARY_API_SECRET"], secure=True)

    url = args.url or sample_url()
    print(f"Image: {url}")
    parts = url.split("/upload/")[1].split("/")
    if parts[0].startswith("v") and parts[0][1:].isdigit():
        parts = parts[1:]
    public_id, _, fmt = "/".join(parts).rpartition(".")
    print(f"public_id={public_id} format={fmt}\n")

    print("1. Public delivery URL")
    print(f"   {http_status(url)}")

    print("2. Account usage (Admin API)")
    try:
        usage = cloudinary.api.usage()
        print(f"   plan={usage.get('plan')}")
        for key in ("storage", "bandwidth", "transformations", "credits"):
            if key in usage:
                print(f"   {key}: {json.dumps(usage[key])}")
        if usage.get("rate_limit_allowed") is not None:
            print(f"   admin api calls left: {usage.get('rate_limit_remaining')}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")

    print("3. Resource lookup (Admin API)")
    try:
        resource = cloudinary.api.resource(public_id)
        print(f"   found: {resource.get('bytes')} bytes, {resource.get('width')}x{resource.get('height')}, "
              f"access_mode={resource.get('access_mode')}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")

    print("4. Signed private download (API)")
    try:
        signed = cloudinary.utils.private_download_url(public_id, fmt, resource_type="image", type="upload")
        print(f"   {http_status(signed)}")
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
