#!/usr/bin/env python3
"""
Test script for ICT Journal functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app

def test_journal():
    """Test journal functionality"""
    print("Creating Flask app...")
    app = create_app()
    
    print("Creating test client...")
    client = app.test_client()
    
    print("Testing journal dashboard...")
    try:
        response = client.get('/api/ict/journal/')
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.content_type}")
        print(f"Response length: {len(response.data)}")
        
        if response.status_code == 200:
            print("✅ Journal dashboard working!")
            # Check if it's HTML
            if 'text/html' in response.content_type:
                print("✅ Returns HTML content")
                # Check for key content
                content = response.data.decode('utf-8', errors='ignore')
                if 'ICT Trading Journal' in content:
                    print("✅ Template rendered correctly")
                else:
                    print("❌ Template content issue")
            else:
                print("❌ Not returning HTML")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_journal()
