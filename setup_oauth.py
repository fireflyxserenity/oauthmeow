"""
Twitch OAuth Setup Helper
This script helps you create a proper OAuth application for your bot.
"""

import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            # Parse the callback URL for the authorization code
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            if 'code' in params:
                self.server.auth_code = params['code'][0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <body>
                    <h2>Authorization Successful!</h2>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
                ''')
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h2>Error: No authorization code received</h2></body></html>')

def setup_oauth():
    print("🔧 Twitch Bot OAuth Setup")
    print("=" * 50)
    
    print("\n📋 Step 1: Create a Twitch Application")
    print("1. Go to: https://dev.twitch.tv/console/apps")
    print("2. Click 'Register Your Application'")
    print("3. Fill in:")
    print("   - Name: YourBotName (e.g., 'MeowBot')")
    print("   - OAuth Redirect URLs: http://localhost:3000/callback")
    print("   - Category: Chat Bot")
    print("4. Click 'Create'")
    print("5. Copy your Client ID and Client Secret")
    
    input("\nPress Enter when you've completed Step 1...")
    
    client_id = input("\n🔑 Enter your Client ID: ").strip()
    client_secret = input("🔐 Enter your Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Client ID and Secret are required!")
        return
    
    # Update .env file
    try:
        with open('.env', 'r') as f:
            content = f.read()
        
        # Replace client ID and secret
        content = content.replace('TWITCH_CLIENT_ID=YOUR_CLIENT_ID_HERE', f'TWITCH_CLIENT_ID={client_id}')
        content = content.replace('TWITCH_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE', f'TWITCH_CLIENT_SECRET={client_secret}')
        
        with open('.env', 'w') as f:
            f.write(content)
        
        print("✅ Updated .env file with your credentials")
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return
    
    print("\n🌐 Step 2: Get Bot Token")
    print("Now we'll get your bot token...")
    
    # Scopes needed for a chat bot
    scopes = "chat:read+chat:edit+channel:moderate+whispers:read+whispers:edit"
    
    # Start local server for OAuth callback
    server = HTTPServer(('localhost', 3000), OAuthHandler)
    server.auth_code = None
    
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Build OAuth URL
    oauth_url = f"https://id.twitch.tv/oauth2/authorize?response_type=code&client_id={client_id}&redirect_uri=http://localhost:3000/callback&scope={scopes}"
    
    print(f"\n🔗 Opening OAuth URL in your browser...")
    print("If it doesn't open automatically, copy this URL:")
    print(oauth_url)
    
    webbrowser.open(oauth_url)
    
    # Wait for authorization
    print("\n⏳ Waiting for authorization...")
    timeout = 120  # 2 minutes
    start_time = time.time()
    
    while server.auth_code is None and (time.time() - start_time) < timeout:
        time.sleep(1)
    
    server.shutdown()
    
    if server.auth_code:
        print("✅ Authorization successful!")
        print(f"📝 Authorization Code: {server.auth_code}")
        print("\n🔄 Now exchanging code for token...")
        
        # Exchange code for token (you'll need to implement this)
        print("⚠️  Manual step required:")
        print("Use this authorization code to get your access token:")
        print(f"Code: {server.auth_code}")
        print("\nOr use the simple token generator for now:")
        print("https://twitchtokengenerator.com/")
        
    else:
        print("❌ Timeout waiting for authorization")
        print("Please try again or use the simple token generator:")
        print("https://twitchtokengenerator.com/")

if __name__ == "__main__":
    setup_oauth()
