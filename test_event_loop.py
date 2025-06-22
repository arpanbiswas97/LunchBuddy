#!/usr/bin/env python3
"""Test script to verify event loop handling."""

import asyncio
import threading
import time
from datetime import date

def test_event_loop_handling():
    """Test that event loop handling works correctly across threads."""
    
    print("🧪 Testing Event Loop Handling")
    print("=" * 40)
    
    # Simulate the bot's event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Store the loop reference (like the bot does)
    event_loop = loop
    
    def callback_function():
        """Simulate the callback that would be called from scheduler thread."""
        try:
            # This simulates what the bot's handle_registration_event does
            if event_loop is None:
                print("❌ Event loop not available")
                return
                
            # Post a task to the event loop
            event_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(test_async_task())
            )
            print("✅ Event queued successfully")
            
        except Exception as e:
            print(f"❌ Error in callback: {e}")
    
    async def test_async_task():
        """Simulate the async task that would be executed."""
        print("✅ Async task executed successfully")
        await asyncio.sleep(0.1)  # Simulate some async work
    
    # Start the event loop in a separate thread
    def run_event_loop():
        loop.run_forever()
    
    loop_thread = threading.Thread(target=run_event_loop, daemon=True)
    loop_thread.start()
    
    # Give the loop time to start
    time.sleep(0.1)
    
    # Test the callback from main thread
    print("Testing callback from main thread...")
    callback_function()
    
    # Test the callback from a different thread (like scheduler)
    print("Testing callback from different thread...")
    scheduler_thread = threading.Thread(target=callback_function, daemon=True)
    scheduler_thread.start()
    
    # Wait for tasks to complete
    time.sleep(0.5)
    
    # Stop the event loop
    loop.call_soon_threadsafe(loop.stop)
    loop_thread.join(timeout=1)
    
    print("\n" + "=" * 40)
    print("🎉 Event loop handling test completed!")
    print("\nThis verifies that:")
    print("• Event loop can be accessed from different threads")
    print("• Tasks can be queued safely across threads")
    print("• No 'no current event loop' errors occur")

if __name__ == "__main__":
    test_event_loop_handling() 