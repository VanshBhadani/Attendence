"""
Test script for the Flask web application
Tests the API endpoints and functionality
"""

import requests
import json
import time

def test_web_application():
    """Test the web application endpoints"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing ERP Attendance Scraper Web Application")
    print("=" * 60)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            print("✅ Test 1 PASSED: Server is running and responding")
        else:
            print(f"❌ Test 1 FAILED: Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Test 1 FAILED: Cannot connect to server - {e}")
        return False
    
    # Test 2: Check API endpoint with invalid data
    try:
        response = requests.post(
            f"{base_url}/scrape",
            json={},
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 400:
            print("✅ Test 2 PASSED: API correctly handles missing roll number")
        else:
            print(f"❌ Test 2 FAILED: Expected 400, got {response.status_code}")
    except Exception as e:
        print(f"❌ Test 2 FAILED: API request failed - {e}")
    
    # Test 3: Check API endpoint with valid roll number (this will take time)
    print("\n🤖 Test 3: Testing actual ERP scraping...")
    print("⏳ This will take 30-60 seconds...")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{base_url}/scrape",
            json={"roll_number": "23R11A0590"},
            headers={'Content-Type': 'application/json'},
            timeout=120  # 2 minute timeout
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Test 3 PASSED: ERP scraping successful in {end_time - start_time:.1f} seconds")
                print(f"📊 Data: {data['attendance']['total_attended']}/{data['attendance']['total_conducted']} ({data['attendance']['percentage']:.2f}%)")
            else:
                print(f"❌ Test 3 FAILED: API returned success=False: {data.get('error')}")
        else:
            print(f"❌ Test 3 FAILED: API returned status {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.Timeout:
        print("❌ Test 3 FAILED: Request timed out (ERP may be slow)")
    except Exception as e:
        print(f"❌ Test 3 FAILED: Scraping request failed - {e}")
    
    print("\n🎯 Testing complete!")
    print("💡 If Test 3 failed, the ERP system might be down or slow")
    print("💡 The web application should still work for manual testing")

if __name__ == "__main__":
    test_web_application()
