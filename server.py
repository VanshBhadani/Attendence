#!/usr/bin/env python3
"""
Simple HTTP Server for Attendance Calculator Website
Run this script to serve the website locally
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

# Configuration
PORT = 8000
HOST = 'localhost'

def main():
    # Change to the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Create server
    handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer((HOST, PORT), handler) as httpd:
            url = f"http://{HOST}:{PORT}"
            print("=" * 60)
            print("🚀 FUTURISTIC ATTENDANCE CALCULATOR SERVER")
            print("=" * 60)
            print(f"📡 Server running at: {url}")
            print(f"📁 Serving files from: {script_dir}")
            print("=" * 60)
            print("💡 Press Ctrl+C to stop the server")
            print("=" * 60)
            
            # Try to open browser automatically
            try:
                webbrowser.open(url)
                print(f"🌐 Opening {url} in your default browser...")
            except Exception as e:
                print(f"⚠️  Could not open browser automatically: {e}")
                print(f"🔗 Please manually open: {url}")
            
            print("\n⚡ Server is running...")
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        sys.exit(0)
    except OSError as e:
        if e.errno == 10048:  # Port already in use
            print(f"❌ Error: Port {PORT} is already in use!")
            print("💡 Try using a different port or close the application using this port")
        else:
            print(f"❌ Error starting server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
