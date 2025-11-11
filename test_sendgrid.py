"""
SendGrid Email Test Script
Run this to test your SendGrid configuration
"""
import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Load environment variables from .env file
load_dotenv()

def test_sendgrid():
    # Get API key from environment
    api_key = os.environ.get('SENDGRID_API_KEY')
    
    if not api_key:
        print("❌ ERROR: SENDGRID_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        return False
    
    print("✅ SendGrid API Key found")
    print(f"   Key starts with: {api_key[:10]}...")
    
    # Create test message
    message = Mail(
        from_email='houzdey@houzdey.com',  # Must be verified in SendGrid
        to_emails='elcollinz@gmail.com',   # Your test email
        subject='Houzdey - SendGrid Test Email',
        html_content='<strong>🎉 SendGrid is working!</strong><br><br>This is a test email from Houzdey backend.'
    )
    
    try:
        print("\n📧 Sending test email...")
        sg = SendGridAPIClient(api_key)
        
        # Uncomment if you're using EU region (for GDPR compliance)
        # sg.set_sendgrid_data_residency("eu")
        
        response = sg.send(message)
        
        print(f"\n✅ SUCCESS! Email sent")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Body: {response.body}")
        print(f"   Message ID: {response.headers.get('X-Message-Id', 'N/A')}")
        
        if response.status_code == 202:
            print("\n🎉 Email accepted by SendGrid!")
            print("   Check your inbox at elcollinz@gmail.com")
            return True
        else:
            print(f"\n⚠️ Unexpected status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        if hasattr(e, 'body'):
            print(f"   Details: {e.body}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("HOUZDEY - SENDGRID EMAIL TEST")
    print("=" * 60)
    
    success = test_sendgrid()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED - SendGrid is configured correctly!")
    else:
        print("❌ TEST FAILED - Please check the errors above")
    print("=" * 60)
