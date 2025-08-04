"""
Debug startup script for Flask app
"""

import sys
import os

print("🔧 Debug Startup Script")
print("=" * 40)

# Check Python version and path
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Current working directory: {os.getcwd()}")

# Check imports
try:
    from flask import Flask
    print("✅ Flask import: SUCCESS")
except ImportError as e:
    print(f"❌ Flask import: FAILED - {e}")
    sys.exit(1)

try:
    from playwright_erp_scraper import scrape_student_data
    print("✅ Scraper import: SUCCESS")
except ImportError as e:
    print(f"❌ Scraper import: FAILED - {e}")

# Check if templates directory exists
templates_path = os.path.join(os.getcwd(), 'templates')
if os.path.exists(templates_path):
    print("✅ Templates directory: EXISTS")
    templates_files = os.listdir(templates_path)
    print(f"   Template files: {templates_files}")
else:
    print("❌ Templates directory: MISSING")

print("\n🚀 Starting Flask Application...")
print("=" * 40)

# Import and run the app
try:
    from app import app
    print("✅ App module imported successfully")
    
    print("🌐 Starting server on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    
except Exception as e:
    print(f"❌ Error starting app: {e}")
    import traceback
    traceback.print_exc()
