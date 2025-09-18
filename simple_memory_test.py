#!/usr/bin/env python3
"""
Simple memory test to debug API issues and test basic memory retention.
"""

import requests
import json
import time

def test_basic_memory():
    """Simple test of memory retention with Mia/Sage."""
    session = requests.Session()

    # Authenticate
    print("🔐 Authenticating...")
    auth_response = session.get("http://localhost:8080/setup")
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return

    print("✅ Authentication successful")

    # Test with correct character UUID
    for character_name, character_id in [("Mia", "e7954557-4736-4e5e-8c6e-0ce0d8618dad")]:
        print(f"\n🧠 Testing memory with character: {character_name} ({character_id[:8]}...)")

        # Plant some facts
        facts = [
            ("My name is Jason", "name", "jason"),
            ("I live in San Rafael, California", "location", "san rafael"),
            ("I'm an emergency physician", "profession", "emergency physician"),
            ("My wife's name is Margaret", "spouse", "margaret"),
            ("I drive a Tesla", "car", "tesla")
        ]

        session_id = None
        conversation_history = []

        # Plant facts
        for i, (statement, fact_type, keyword) in enumerate(facts, 1):
            try:
                payload = {
                    "message": statement,
                    "character_id": character_id,
                    "session_id": session_id,
                    "use_documents": False
                }

                response = session.post("http://localhost:8080/api/chat", json=payload)
                print(f"Exchange {i}: Status {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"Response type: {type(data)}")

                    if isinstance(data, dict):
                        ai_response = data.get("response", "No response")
                        session_id = data.get("session_id") or session_id
                        print(f"✅ AI: {ai_response[:100]}...")
                        conversation_history.append((statement, ai_response, fact_type, keyword))
                    elif isinstance(data, list):
                        print(f"⚠️  List response: {data}")
                        if len(data) >= 2 and isinstance(data[0], dict):
                            error_msg = data[0].get("error", "Unknown error")
                            print(f"❌ Error: {error_msg}")
                            break
                    else:
                        print(f"❌ Unexpected response format: {type(data)}")
                        print(f"Raw response: {data}")
                        break
                else:
                    print(f"❌ HTTP Error: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"Error details: {error_data}")
                    except:
                        print(f"Error text: {response.text}")
                    break

                time.sleep(1)

            except Exception as e:
                print(f"❌ Exception: {e}")
                break

        # Now test memory recall
        if conversation_history:
            print(f"\n🔍 Testing memory recall after {len(conversation_history)} exchanges:")

            test_questions = [
                ("What is my name?", "name", "jason"),
                ("Where do I live?", "location", "san rafael"),
                ("What is my profession?", "profession", "emergency physician"),
                ("What is my wife's name?", "spouse", "margaret"),
                ("What car do I drive?", "car", "tesla")
            ]

            for question, fact_type, expected_keyword in test_questions:
                try:
                    payload = {
                        "message": question,
                        "character_id": character_id,
                        "session_id": session_id,
                        "use_documents": False
                    }

                    response = session.post("http://localhost:8080/api/chat", json=payload)

                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, dict):
                            ai_response = data.get("response", "")
                            remembered = expected_keyword.lower() in ai_response.lower()
                            status = "✅ REMEMBERED" if remembered else "❌ FORGOTTEN"
                            print(f"  {question} -> {status}")
                            print(f"    Response: {ai_response[:100]}...")
                        else:
                            print(f"  {question} -> ❌ API ERROR (list response)")
                    else:
                        print(f"  {question} -> ❌ HTTP ERROR ({response.status_code})")

                    time.sleep(1)

                except Exception as e:
                    print(f"  {question} -> ❌ EXCEPTION: {e}")

        print(f"\n" + "="*50)

if __name__ == "__main__":
    test_basic_memory()