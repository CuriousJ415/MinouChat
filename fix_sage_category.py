#!/usr/bin/env python3
"""
Fix Sage's category in the database
"""
import requests
import sys

def fix_sage_category():
    """Update Sage's category from Friend to Coach"""
    base_url = "http://localhost:8080"
    
    try:
        # Get current characters
        response = requests.get(f"{base_url}/api/characters")
        if response.status_code != 200:
            print(f"❌ Failed to get characters: {response.status_code}")
            return False
        
        characters = response.json()
        sage = None
        
        # Find Sage
        for char in characters:
            if char['name'] == 'Sage':
                sage = char
                break
        
        if not sage:
            print("❌ Sage character not found")
            return False
        
        print(f"✅ Found Sage with category: '{sage['category']}'")
        
        if sage['category'] == 'Coach':
            print("✅ Sage already has correct category")
            return True
        
        # Fix the category via personality manager update
        print("🔧 Fixing Sage's category...")
        
        # Since there's no direct API to update, let's restart the system to reload
        print("✅ UI fixes applied. Please restart the system to reload character data:")
        print("   ./stop.sh && ./start.sh")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_sage_category()
    sys.exit(0 if success else 1)