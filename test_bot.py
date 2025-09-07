#!/usr/bin/env python3
"""
Quick test to verify the bot can start and the Flask server is working
"""

import sys
import os
import time
import requests
import threading
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_flask_server():
    """Test if the Flask server responds"""
    time.sleep(2)  # Wait for server to start
    try:
        response = requests.get('http://localhost:3000/api/health', timeout=5)
        if response.status_code == 200:
            print("✅ Flask server is working!")
            print(f"Response: {response.json()}")
        else:
            print(f"❌ Flask server responded with status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to Flask server: {e}")

def main():
    print("🧪 Testing Meow Bot Flask integration...")
    
    # Start test in background
    test_thread = threading.Thread(target=test_flask_server)
    test_thread.daemon = True
    test_thread.start()
    
    # Import and run bot (this will start Flask server)
    try:
        import meow_bot
        print("✅ Bot imports successfully!")
        
        # This would start the bot, but we'll just test the Flask server
        print("🚀 Starting bot for 10 seconds to test Flask server...")
        
        # Import the flask app directly
        from meow_bot import flask_app
        
        # Start Flask in a thread
        flask_thread = threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=3000, debug=False))
        flask_thread.daemon = True
        flask_thread.start()
        
        # Wait for test
        test_thread.join(timeout=10)
        
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
