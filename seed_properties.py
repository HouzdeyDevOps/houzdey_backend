"""
Property Seeding Script
Reads scraped property data from JSON and uploads to Houzdey API
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
import sys

# Configuration
API_BASE_URL = "https://api.houzdey.com/api/v1"
LOGIN_ENDPOINT = f"{API_BASE_URL}/auth/login"
PROPERTIES_ENDPOINT = f"{API_BASE_URL}/properties"

# Credentials
EMAIL = "elcollinz@gmail.com"
PASSWORD = "Adminpassword123@#$"

# Stats tracking
stats = {
    "total": 0,
    "successful": 0,
    "failed": 0,
    "errors": []
}


def login() -> Optional[str]:
    """Authenticate and get Bearer token"""
    try:
        print("🔐 Authenticating with Houzdey API...")
        response = requests.post(
            LOGIN_ENDPOINT,
            json={"email": EMAIL, "password": PASSWORD}
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        print("✓ Authentication successful")
        return token
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return None


def upload_property(property_data: Dict, token: str, index: int) -> bool:
    """Upload a single property with images to the API"""
    try:
        title = property_data.get("title", "Unknown")
        print(f"\n[{index}] Uploading: {title}")
        
        # Prepare multipart form data
        files = []
        data = {}
        
        # Add text fields
        for key, value in property_data.items():
            if key == "image_paths":
                continue  # Handle separately
            elif key == "amenities":
                # Convert amenities array to JSON string
                data[key] = json.dumps(value)
            elif key == "source_url":
                continue  # Don't send source_url to API
            else:
                data[key] = value
        
        # Add image files
        image_paths = property_data.get("image_paths", [])
        if not image_paths:
            print(f"  ⚠ Warning: No images found, skipping property")
            stats["failed"] += 1
            stats["errors"].append({
                "property": title,
                "error": "No images"
            })
            return False
        
        for img_path in image_paths:
            img_file = Path(img_path)
            if img_file.exists():
                files.append(
                    ("images", (img_file.name, open(img_file, "rb"), "image/jpeg"))
                )
            else:
                print(f"  ⚠ Warning: Image not found: {img_path}")
        
        if not files:
            print(f"  ✗ No valid image files found, skipping")
            stats["failed"] += 1
            stats["errors"].append({
                "property": title,
                "error": "No valid image files"
            })
            return False
        
        # Send POST request
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            PROPERTIES_ENDPOINT,
            data=data,
            files=files,
            headers=headers
        )
        
        # Close file handles
        for _, file_tuple in files:
            file_tuple[1].close()
        
        if response.status_code == 201:
            print(f"  ✓ SUCCESS - Property created")
            stats["successful"] += 1
            return True
        else:
            error_msg = response.json().get("detail", response.text)
            print(f"  ✗ FAILED - {response.status_code}: {error_msg}")
            stats["failed"] += 1
            stats["errors"].append({
                "property": title,
                "error": f"{response.status_code}: {error_msg}"
            })
            return False
            
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        stats["failed"] += 1
        stats["errors"].append({
            "property": property_data.get("title", "Unknown"),
            "error": str(e)
        })
        return False


def seed_properties(json_file: str, delay: float = 2.0):
    """Main seeding function"""
    
    # Load JSON data
    json_path = Path(json_file)
    if not json_path.exists():
        print(f"✗ JSON file not found: {json_file}")
        return
    
    print(f"📂 Loading data from: {json_file}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    properties = data.get("properties", [])
    stats["total"] = len(properties)
    
    print(f"📊 Found {stats['total']} properties to upload")
    
    # Authenticate
    token = login()
    if not token:
        print("Cannot proceed without authentication")
        return
    
    # Upload each property
    print(f"\n{'='*60}")
    print("Starting property upload...")
    print(f"{'='*60}")
    
    for index, property_data in enumerate(properties, start=1):
        upload_property(property_data, token, index)
        
        # Rate limiting
        if index < len(properties):
            time.sleep(delay)
    
    # Print summary
    print(f"\n{'='*60}")
    print("UPLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"Total Properties: {stats['total']}")
    print(f"✓ Successful: {stats['successful']}")
    print(f"✗ Failed: {stats['failed']}")
    print(f"Success Rate: {(stats['successful']/stats['total']*100):.1f}%")
    
    if stats["errors"]:
        print(f"\n❌ Failed Properties ({len(stats['errors'])}):")
        for i, error in enumerate(stats["errors"][:10], start=1):  # Show first 10
            print(f"{i}. {error['property']} - {error['error']}")
        
        if len(stats["errors"]) > 10:
            print(f"... and {len(stats['errors']) - 10} more")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python seed_properties.py <json_file>")
        print("Example: python seed_properties.py ./scraped_data/properties_scraped_2025-12-01_10-30-00.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    # Optional: delay between requests (default 2 seconds)
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    
    seed_properties(json_file, delay)
