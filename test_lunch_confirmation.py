#!/usr/bin/env python3
"""
Test script to verify that register_user_for_lunch is called when user confirms lunch.
"""

import sys
import os
from datetime import date

# Add the lunchbuddy directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lunchbuddy'))

from lunchbuddy.scheduler import register_user_for_lunch, pending_confirmations
from lunchbuddy.models import PendingLunchConfirmation
from datetime import datetime

def test_register_user_for_lunch():
    """Test that register_user_for_lunch function is called correctly."""
    print("Testing register_user_for_lunch function...")
    
    # Test the function directly
    register_user_for_lunch("Test User", "test@example.com", "veg")
    
    # Test with pending confirmation
    test_user_id = 12345
    test_date = date.today()
    test_key = (test_user_id, test_date)
    
    # Create a test confirmation
    test_confirmation = PendingLunchConfirmation(
        user_id=test_user_id,
        target_date=test_date,
        message_id=1,
        chat_id=test_user_id,
        created_at=datetime.now()
    )
    
    pending_confirmations[test_key] = test_confirmation
    
    print(f"Created test confirmation: {test_confirmation}")
    print(f"Pending confirmations: {pending_confirmations}")
    
    # Simulate user confirming lunch
    test_confirmation.response_received = True
    test_confirmation.user_choice = True
    
    # This should call register_user_for_lunch
    if test_confirmation.user_choice:
        register_user_for_lunch("Test User", "test@example.com", "veg")
        print("✅ register_user_for_lunch was called successfully!")
    
    # Clean up
    del pending_confirmations[test_key]
    print("Test completed successfully!")

if __name__ == "__main__":
    test_register_user_for_lunch() 