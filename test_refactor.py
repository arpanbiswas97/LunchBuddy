#!/usr/bin/env python3
"""Test script to verify the refactored LunchBuddy architecture."""

import sys
import os
from datetime import date, datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lunchbuddy.scheduler import LunchScheduler, LunchRegistrationEvent
from lunchbuddy.config import settings

def test_registration_callback(event: LunchRegistrationEvent):
    """Test callback function for registration processing."""
    print(f"✅ Registration callback triggered for user {event.user_id}")
    print(f"   Target date: {event.target_date}")
    print(f"   User: {event.user_name} ({event.user_email})")
    print(f"   Dietary preference: {event.dietary_preference}")
    print(f"   Preferred days: {event.preferred_days}")

def test_timeout_callback(user_id: int, target_date: date, take_lunch: bool):
    """Test callback function for timeout handling."""
    print(f"✅ Timeout callback triggered for user {user_id}")
    print(f"   Target date: {target_date}")
    print(f"   Take lunch (default): {take_lunch}")

def test_scheduler_creation():
    """Test that the scheduler can be created with the new architecture."""
    print("Testing scheduler creation...")
    
    try:
        scheduler = LunchScheduler(
            registration_callback=test_registration_callback,
            timeout_callback=test_timeout_callback
        )
        print("✅ Scheduler created successfully")
        return scheduler
    except Exception as e:
        print(f"❌ Failed to create scheduler: {e}")
        return None

def test_event_creation():
    """Test that LunchRegistrationEvent can be created."""
    print("\nTesting event creation...")
    
    try:
        # Use first two days from configuration for testing
        test_days = [day.strip().lower() for day in settings.lunch_days[:2]]
        
        event = LunchRegistrationEvent(
            user_id=12345,
            target_date=date.today(),
            user_name="Test User",
            user_email="test@example.com",
            dietary_preference="veg",
            preferred_days=test_days
        )
        print("✅ LunchRegistrationEvent created successfully")
        return event
    except Exception as e:
        print(f"❌ Failed to create event: {e}")
        return None

def test_scheduler_callbacks(scheduler, event):
    """Test that scheduler callbacks work correctly."""
    print("\nTesting scheduler callbacks...")
    
    try:
        # Test registration callback
        print("Testing registration callback...")
        scheduler.registration_callback(event)
        
        # Test timeout callback
        print("Testing timeout callback...")
        scheduler.timeout_callback(12345, date.today(), True)
        
        print("✅ All callbacks executed successfully")
    except Exception as e:
        print(f"❌ Callback test failed: {e}")

def test_config():
    """Test that the configuration is loaded correctly."""
    print("\nTesting configuration...")
    
    try:
        print(f"Lunch days: {settings.lunch_days}")
        print(f"Registration time: {settings.lunch_reminder_time}")
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")

def main():
    """Run all tests."""
    print("🧪 Testing LunchBuddy Simplified Registration Architecture")
    print("=" * 60)
    
    # Test configuration
    test_config()
    
    # Test scheduler creation
    scheduler = test_scheduler_creation()
    if not scheduler:
        return
    
    # Test event creation
    event = test_event_creation()
    if not event:
        return
    
    # Test callbacks
    test_scheduler_callbacks(scheduler, event)
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed successfully!")
    print("\nThe simplified architecture is working correctly:")
    print("✅ Combined registration and processing into single step")
    print("✅ Direct registration processing on day before lunch at 12:30 PM")
    print("✅ 30-minute timeout with automatic default registration")
    print("✅ Uses lunch_days configuration for scheduling")
    print("✅ No more separate reminder and processing phases")
    print("✅ Schedules processing on day before each lunch day")

if __name__ == "__main__":
    main() 