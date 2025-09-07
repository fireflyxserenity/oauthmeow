#!/usr/bin/env python3
"""
Clear Railway Queue - Emergency Channel Queue Cleaner
Run this if Railway keeps returning the same channels
"""
import requests

def clear_railway_queue():
    """Clear the Railway queue by polling until empty"""
    railway_url = 'https://oauthmeow-production.up.railway.app'
    
    print("🧹 Clearing Railway queue...")
    
    # Poll multiple times to clear any stuck channels
    for i in range(5):
        try:
            response = requests.get(f'{railway_url}/api/pending-channels', timeout=10)
            if response.status_code == 200:
                data = response.json()
                channels = data.get('channels', [])
                print(f"Attempt {i+1}: Found {len(channels)} channels in queue")
                if len(channels) == 0:
                    print("✅ Queue is now empty!")
                    break
                else:
                    for ch in channels:
                        print(f"  - {ch.get('channel', 'unknown')}")
            else:
                print(f"❌ Error: {response.status_code}")
                break
        except Exception as e:
            print(f"❌ Error clearing queue: {e}")
            break
    
    print("🎉 Railway queue clearing complete!")

if __name__ == "__main__":
    clear_railway_queue()
