"""
Termii API Test Script
Tests the Termii API credentials and displays account information
"""

import requests
import json
from typing import Dict, Any

# Termii API Configuration
TERMII_API_KEY = "TLCUuIjgxxslyjpbsATanjFozmOfQNykrJTgamKzNrxtydRPZPkshGrVwtVhKu"
TERMII_BASE_URL = "https://v3.api.termii.com"

def test_balance() -> Dict[str, Any]:
    """
    Test API by fetching account balance
    Endpoint: GET /api/get-balance
    """
    url = f"{TERMII_BASE_URL}/api/get-balance"
    params = {"api_key": TERMII_API_KEY}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
            "response": e.response.text if hasattr(e, 'response') and e.response else None
        }

def test_sender_ids() -> Dict[str, Any]:
    """
    Test API by fetching sender IDs
    Endpoint: GET /api/sender-id
    """
    url = f"{TERMII_BASE_URL}/api/sender-id"
    params = {"api_key": TERMII_API_KEY}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return {
            "success": True,
            "status_code": response.status_code,
            "data": response.json()
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
            "response": e.response.text if hasattr(e, 'response') and e.response else None
        }

def print_result(title: str, result: Dict[str, Any]) -> None:
    """Pretty print test results"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    
    if result["success"]:
        print(f"✅ Status: SUCCESS (HTTP {result['status_code']})")
        print(f"\n📊 Response Data:")
        print(json.dumps(result["data"], indent=2))
    else:
        print(f"❌ Status: FAILED")
        if result.get("status_code"):
            print(f"HTTP Status Code: {result['status_code']}")
        print(f"\n⚠️  Error: {result['error']}")
        if result.get("response"):
            print(f"\n📄 Response:")
            try:
                print(json.dumps(json.loads(result["response"]), indent=2))
            except:
                print(result["response"])

def main():
    """Run all Termii API tests"""
    print("\n🚀 Testing Termii API Credentials...")
    print(f"API Key: {TERMII_API_KEY[:10]}...")
    print(f"Base URL: {TERMII_BASE_URL}")
    
    # Test 1: Check Balance
    balance_result = test_balance()
    print_result("Test 1: Account Balance", balance_result)
    
    # Test 2: Get Sender IDs
    sender_ids_result = test_sender_ids()
    print_result("Test 2: Sender IDs", sender_ids_result)
    
    # Summary
    print(f"\n{'='*60}")
    print("  📋 SUMMARY")
    print(f"{'='*60}")
    
    tests_passed = sum([
        balance_result["success"],
        sender_ids_result["success"]
    ])
    
    print(f"Tests Passed: {tests_passed}/2")
    
    if tests_passed == 2:
        print("✅ All tests passed! Your Termii API is working correctly.")
        
        # Display useful information
        if balance_result["success"]:
            balance_data = balance_result["data"]
            print(f"\n💰 Account Balance: {balance_data.get('balance', 'N/A')} {balance_data.get('currency', '')}")
        
        if sender_ids_result["success"]:
            sender_ids = sender_ids_result["data"].get('data', [])
            print(f"\n📱 Available Sender IDs: {len(sender_ids)}")
            for sender in sender_ids:
                print(f"   - {sender.get('sender_id')} (Status: {sender.get('status')})")
    else:
        print("❌ Some tests failed. Please check your API key and try again.")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
