#!/usr/bin/env python3
"""
Quick debug test for semantic memory.
"""

import requests
import time

def test_debug_memory():
    """Test memory with debug logging enabled."""
    session = requests.Session()

    # Authenticate
    print("🔐 Authenticating...")
    auth_response = session.get("http://localhost:8080/setup")
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return

    character_id = "e7954557-4736-4e5e-8c6e-0ce0d8618dad"  # Mia
    session_id = None

    print("🧠 Quick memory debug test...")

    # Send a test message
    print("📍 Sending test message...")
    payload = {
        "message": "My name is TestUser and I like debugging",
        "character_id": character_id,
        "session_id": session_id,
        "use_documents": False
    }

    response = session.post("http://localhost:8080/api/chat", json=payload)

    if response.status_code == 200:
        data = response.json()
        if isinstance(data, dict):
            ai_response = data.get("response", "")
            session_id = data.get("session_id") or session_id
            print(f"✅ Response: {ai_response[:100]}...")
        else:
            print(f"❌ API error")
            return
    else:
        print(f"❌ HTTP error {response.status_code}")
        return

    print("Now check the docker logs for debug information!")

if __name__ == "__main__":
    test_debug_memory()