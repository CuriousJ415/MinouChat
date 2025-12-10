#!/usr/bin/env python3
"""
Focused memory test to find the exact memory cliff around 7-10 exchanges.
"""

import requests
import time

def test_memory_cliff():
    """Test memory retention around the suspected 7-10 exchange limit."""
    session = requests.Session()

    # Authenticate
    print("🔐 Authenticating...")
    auth_response = session.get("http://localhost:8080/setup")
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return

    character_id = "e7954557-4736-4e5e-8c6e-0ce0d8618dad"  # Mia
    session_id = None

    # Plant key facts early in conversation
    key_facts = [
        ("My name is Jason Rodriguez", "name", "jason", 1),
        ("I live in San Rafael, California", "location", "san rafael", 2),
        ("My wife's name is Margaret", "spouse", "margaret", 3),
        ("I work as an emergency physician", "profession", "emergency physician", 4),
    ]

    # Filler conversation to push past memory limit
    filler_conversation = [
        "How's the weather today?",
        "What do you think about artificial intelligence?",
        "Can you help me organize my schedule?",
        "What are some good restaurants in the Bay Area?",
        "How should I prepare for a busy day at work?",
        "What's your opinion on electric vehicles?",
        "Can you suggest some productivity tips?",
        "What are some good books to read?",
        "How can I maintain work-life balance?",
        "What are some healthy meal ideas?",
        "How do I stay motivated during difficult times?",
        "What are some effective stress management techniques?",
    ]

    print(f"🧠 Testing memory cliff with {len(key_facts)} facts + {len(filler_conversation)} filler exchanges...")

    # Plant key facts
    print("\n📍 Planting key facts:")
    for message, fact_type, keyword, position in key_facts:
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
                    print(f"  ✅ Exchange {position}: Planted '{fact_type}' - {ai_response[:40]}...")
                else:
                    print(f"  ❌ Exchange {position}: API error")
                    return
            else:
                print(f"  ❌ Exchange {position}: HTTP error {response.status_code}")
                return

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ Exchange {position}: Exception {e}")
            return

    # Add filler conversation
    print(f"\n💬 Adding {len(filler_conversation)} filler exchanges:")
    for i, message in enumerate(filler_conversation, len(key_facts) + 1):
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
                    print(f"  ✅ Exchange {i:2d}: {message[:30]}... -> {ai_response[:30]}...")

                    # Test memory every few exchanges
                    if i in [6, 8, 10, 12, 15]:
                        print(f"\n🔍 Memory check at exchange {i}:")
                        test_memory_recall(session, character_id, session_id, key_facts, i)
                        print()

                else:
                    print(f"  ❌ Exchange {i}: API error")
                    break
            else:
                print(f"  ❌ Exchange {i}: HTTP error {response.status_code}")
                break

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ Exchange {i}: Exception {e}")
            break

    # Final comprehensive memory test
    total_exchanges = len(key_facts) + len(filler_conversation)
    print(f"\n🎯 Final memory test after {total_exchanges} total exchanges:")
    test_memory_recall(session, character_id, session_id, key_facts, total_exchanges, detailed=True)

def test_memory_recall(session, character_id, session_id, key_facts, current_exchange, detailed=False):
    """Test recall of planted facts."""

    test_questions = [
        ("What is my name?", "name", "jason"),
        ("Where do I live?", "location", "san rafael"),
        ("What is my wife's name?", "spouse", "margaret"),
        ("What is my profession?", "profession", "emergency physician"),
    ]

    results = []

    for question, fact_type, expected_keyword in test_questions:
        # Find when this fact was planted
        planted_at = next((f[3] for f in key_facts if f[1] == fact_type), None)
        exchanges_ago = current_exchange - planted_at if planted_at else None

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
                    status = "✅" if remembered else "❌"

                    results.append((fact_type, remembered, exchanges_ago))

                    if detailed:
                        print(f"    {status} {question} ({exchanges_ago} exchanges ago)")
                        if not remembered:
                            print(f"        Expected '{expected_keyword}' but got: {ai_response[:60]}...")
                    else:
                        print(f"    {status} {fact_type} ({exchanges_ago} ago)")

            time.sleep(0.2)

        except Exception as e:
            print(f"    ❌ {question}: Exception {e}")

    # Summary for this checkpoint
    remembered_count = len([r for r in results if r[1]])
    total_count = len(results)
    success_rate = remembered_count / total_count * 100 if total_count > 0 else 0

    print(f"    📊 Memory retention: {remembered_count}/{total_count} ({success_rate:.1f}%)")

    return results

if __name__ == "__main__":
    test_memory_cliff()