#!/usr/bin/env python3
"""
Quick test to verify semantic memory is working.
"""

import requests
import time

def test_semantic_working():
    """Test that semantic memory retrieval is working."""
    session = requests.Session()

    # Authenticate
    print("🔐 Authenticating...")
    auth_response = session.get("http://localhost:8080/setup")
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return

    character_id = "e7954557-4736-4e5e-8c6e-0ce0d8618dad"  # Mia
    session_id = None

    print("🧠 Testing semantic memory...")

    # Plant early facts
    early_facts = [
        "My name is Alice and I live in Portland",
        "I work as a software engineer at TechCorp",
        "I have a cat named Whiskers",
    ]

    print("📍 Planting facts:")
    for message in early_facts:
        try:
            payload = {
                "message": message,
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
                    print(f"  ✅ {message}")
                else:
                    print(f"  ❌ API error")
                    return
            else:
                print(f"  ❌ HTTP error {response.status_code}")
                return

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            return

    # Add filler conversation
    print("\n💬 Adding filler conversation:")
    filler = [
        "What's the weather like?",
        "Tell me about productivity tips",
        "How can I manage my time better?",
        "What are good exercise routines?",
        "Tell me about healthy eating",
    ]

    for message in filler:
        try:
            payload = {
                "message": message,
                "character_id": character_id,
                "session_id": session_id,
                "use_documents": False
            }

            response = session.post("http://localhost:8080/api/chat", json=payload)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    print(f"  ✅ {message}")
                else:
                    print(f"  ❌ API error")
                    break
            else:
                print(f"  ❌ HTTP error {response.status_code}")
                break

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            break

    # Test semantic recall
    print(f"\n🔍 Testing semantic memory recall:")

    memory_tests = [
        ("What is my name?", "alice"),
        ("Where do I live?", "portland"),
        ("What is my job?", "software engineer"),
        ("What is my cat's name?", "whiskers"),
    ]

    successful_recalls = 0
    total_tests = len(memory_tests)

    for question, expected_keyword in memory_tests:
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

                    if remembered:
                        successful_recalls += 1
                        print(f"  ✅ RECALLED: {question} -> Found '{expected_keyword}'")
                    else:
                        print(f"  ❌ FORGOTTEN: {question} -> Expected '{expected_keyword}'")
                        print(f"    Response: {ai_response[:100]}...")

                else:
                    print(f"  ❌ API ERROR: {question}")
            else:
                print(f"  ❌ HTTP ERROR {response.status_code}: {question}")

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ EXCEPTION: {question} - {e}")

    # Results
    success_rate = successful_recalls / total_tests * 100
    print(f"\n📊 SEMANTIC MEMORY RESULTS:")
    print(f"   Successful recalls: {successful_recalls}/{total_tests}")
    print(f"   Success rate: {success_rate:.1f}%")

    if success_rate >= 75:
        print("🎉 EXCELLENT: Semantic memory is working!")
    elif success_rate >= 50:
        print("✅ GOOD: Semantic memory is functional")
    else:
        print("❌ POOR: Semantic memory needs work")

    return success_rate

if __name__ == "__main__":
    test_semantic_working()