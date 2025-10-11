import os
import sys
import razorpay
from decimal import Decimal

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doctor_appointment.settings")

import django
django.setup()

from django.conf import settings

def test_razorpay_integration():
    """Test basic Razorpay integration"""
    print("Testing Razorpay integration...")
    
    # Print the keys (first 5 characters for security)
    print(f"Razorpay Key ID: {settings.RAZORPAY_KEY_ID[:5]}***")
    print(f"Razorpay Secret: {settings.RAZORPAY_KEY_SECRET[:5]}***")
    
    try:
        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Create a test order
        amount = Decimal('500.00')  # ₹500
        amount_in_paisa = int(amount * 100)  # Convert to paisa
        
        order_data = {
            'amount': amount_in_paisa,
            'currency': 'INR',
            'receipt': 'test_receipt_123',
            'notes': {
                'test': 'This is a test order'
            }
        }
        
        print(f"Creating test order with amount {amount_in_paisa} paisa...")
        order = client.order.create(data=order_data)
        
        print("Order created successfully!")
        print(f"Order ID: {order['id']}")
        print(f"Amount: {order['amount']} paisa")
        print(f"Currency: {order['currency']}")
        
        print("\nRazorpay integration is working correctly!")
        return True
    
    except Exception as e:
        print(f"Error in Razorpay integration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_razorpay_integration() 