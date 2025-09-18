#!/usr/bin/env python3
"""
Test semantic memory integration.
"""

import requests
import time

def test_semantic_memory():
    """Test that semantic memory is working."""
    session = requests.Session()

    # Authenticate
    print("🔐 Authenticating...")
    auth_response = session.get("http://localhost:8080/setup")
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return

    character_id = "e7954557-4736-4e5e-8c6e-0ce0d8618dad"  # Mia
    session_id = None

    print("🧠 Testing semantic memory integration...")

    # Plant early facts
    early_facts = [
        ("My name is Jason and I'm a doctor", "name/profession"),
        ("I live in San Rafael with my wife Margaret", "location/spouse"),
        ("I have two dogs named Patina and Lani", "pets"),
    ]

    print("📍 Planting early facts:")
    for message, fact_type in early_facts:
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
                    print(f"  ✅ Planted: {fact_type} -> {ai_response[:50]}...")
                else:
                    print(f"  ❌ API error for {fact_type}")
                    return
            else:
                print(f"  ❌ HTTP error {response.status_code} for {fact_type}")
                return

            time.sleep(0.5)

        except Exception as e:
            print(f"  ❌ Exception for {fact_type}: {e}")
            return

    # Add lots of filler to push past memory limits
    print("\n💬 Adding filler conversation to test semantic search:")
    filler = [
        "Tell me about the weather patterns.",
        "What are some good productivity tips?",
        "How should I organize my workspace?",
        "What are some healthy breakfast ideas?",
        "Tell me about time management strategies.",
        "What books would you recommend?",
        "How can I improve my sleep schedule?",
        "What are some stress relief techniques?",
        "Tell me about exercise routines.",
        "What are some good habits to develop?",
        "How can I be more environmentally conscious?",
        "What are some creative hobbies to try?",
        "Tell me about nutrition basics.",
        "What are some travel tips?",
        "How can I learn new skills effectively?",
    ]

    for i, message in enumerate(filler, 1):
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
                    print(f"  ✅ Filler {i:2d}: {message[:25]}... -> {ai_response[:30]}...")
                else:
                    print(f"  ❌ API error at filler {i}")
                    break
            else:
                print(f"  ❌ HTTP error {response.status_code} at filler {i}")
                break

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ Exception at filler {i}: {e}")
            break

    # Now test semantic memory recall
    print(f"\n🔍 Testing semantic memory recall after many exchanges:")

    memory_tests = [
        ("What is my name?", "jason", "Should recall from early conversation"),
        ("Where do I live?", "san rafael", "Should recall location"),
        ("What is my wife's name?", "margaret", "Should recall spouse name"),
        ("What are my dogs' names?", "patina", "Should recall pet names"),
        ("What is my profession?", "doctor", "Should recall profession"),
    ]

    successful_recalls = 0
    total_tests = len(memory_tests)

    for question, expected_keyword, description in memory_tests:
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
                        status = "✅ SEMANTIC RECALL"
                        print(f"  {status}: {question}")
                        print(f"    Found '{expected_keyword}' in: {ai_response[:60]}...")
                    else:
                        status = "❌ FORGOTTEN"
                        print(f"  {status}: {question}")
                        print(f"    Expected '{expected_keyword}' but got: {ai_response[:60]}...")

                else:
                    print(f"  ❌ API ERROR: {question}")
            else:
                print(f"  ❌ HTTP ERROR {response.status_code}: {question}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  ❌ EXCEPTION: {question} - {e}")

    # Results
    success_rate = successful_recalls / total_tests * 100
    print(f"\n📊 SEMANTIC MEMORY PERFORMANCE:")
    print(f"   Successful recalls: {successful_recalls}/{total_tests}")
    print(f"   Success rate: {success_rate:.1f}%")

    if success_rate >= 80:
        print("🎉 EXCELLENT: Semantic memory is working well!")
    elif success_rate >= 60:
        print("✅ GOOD: Semantic memory is functional")
    elif success_rate >= 40:
        print("⚠️  PARTIAL: Some semantic memory functionality")
    else:
        print("❌ POOR: Semantic memory may not be working")

    return success_rate

if __name__ == "__main__":
    test_semantic_memory()