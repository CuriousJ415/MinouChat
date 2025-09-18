#!/usr/bin/env python3
"""
Extended memory test to find the exact point where memory starts failing.
"""

import requests
import time

def test_extended_memory():
    """Test memory retention over a longer conversation."""
    session = requests.Session()

    # Authenticate
    print("🔐 Authenticating...")
    auth_response = session.get("http://localhost:8080/setup")
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return

    character_id = "e7954557-4736-4e5e-8c6e-0ce0d8618dad"  # Mia
    session_id = None

    # Extended conversation to test memory limits
    conversation = [
        # Plant key facts early (exchanges 1-5)
        ("My name is Jason Rodriguez", "name", "jason"),
        ("I live in San Rafael, California", "location", "san rafael"),
        ("I work as an emergency physician", "profession", "emergency physician"),
        ("My wife's name is Margaret", "spouse", "margaret"),
        ("I drive a Tesla Model 3", "car", "tesla"),

        # Add more conversation to push memory limits (exchanges 6-15)
        ("I work at Marin General Hospital", "workplace", "marin general"),
        ("My favorite hobby is photography", "hobby", "photography"),
        ("I have two dogs named Max and Luna", "pets", "max luna"),
        ("I was born in Chicago", "birthplace", "chicago"),
        ("My favorite coffee shop is Philz Coffee", "coffee", "philz"),
        ("I graduated from UCSF medical school", "education", "ucsf"),
        ("My specialty is trauma medicine", "specialty", "trauma"),
        ("I play guitar in my spare time", "instrument", "guitar"),
        ("My birthday is March 15th", "birthday", "march 15"),
        ("I love hiking in Muir Woods", "hiking", "muir woods"),

        # Add even more to test long-term memory (exchanges 16-20)
        ("My brother's name is Michael", "brother", "michael"),
        ("I own a sailboat named Serenity", "boat", "serenity"),
        ("My medical license number is CA123456", "license", "ca123456"),
        ("I volunteer at the local animal shelter", "volunteer", "animal shelter"),
        ("My favorite restaurant is The French Laundry", "restaurant", "french laundry"),
    ]

    print(f"🧠 Starting extended memory test with {len(conversation)} exchanges...")

    # Conduct conversation
    for i, (message, fact_type, keyword) in enumerate(conversation, 1):
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
                    print(f"✅ Exchange {i:2d}: Planted '{fact_type}' -> {ai_response[:50]}...")
                else:
                    print(f"❌ Exchange {i:2d}: API returned list format")
                    break
            else:
                print(f"❌ Exchange {i:2d}: HTTP error {response.status_code}")
                break

            time.sleep(0.5)  # Brief pause

        except Exception as e:
            print(f"❌ Exchange {i:2d}: Exception {e}")
            break

    # Now test memory recall at different intervals
    print(f"\n🔍 Testing memory recall after {len(conversation)} exchanges:")
    print("="*60)

    test_questions = [
        # Early facts (should be remembered if context window > 20)
        ("What is my name?", "name", "jason", 1),
        ("Where do I live?", "location", "san rafael", 2),
        ("What is my profession?", "profession", "emergency physician", 3),
        ("What is my wife's name?", "spouse", "margaret", 4),
        ("What car do I drive?", "car", "tesla", 5),

        # Middle facts (test medium-term memory)
        ("Where do I work?", "workplace", "marin general", 6),
        ("What is my hobby?", "hobby", "photography", 7),
        ("What are my dogs' names?", "pets", "max", 8),
        ("Where was I born?", "birthplace", "chicago", 9),
        ("What is my favorite coffee shop?", "coffee", "philz", 10),

        # Later facts (test if recent memory is retained)
        ("What medical school did I attend?", "education", "ucsf", 11),
        ("What is my medical specialty?", "specialty", "trauma", 12),
        ("What instrument do I play?", "instrument", "guitar", 13),
        ("When is my birthday?", "birthday", "march", 14),
        ("Where do I like to hike?", "hiking", "muir woods", 15),

        # Most recent facts (should definitely be remembered)
        ("What is my brother's name?", "brother", "michael", 16),
        ("What is my boat called?", "boat", "serenity", 17),
        ("What is my medical license number?", "license", "ca123456", 18),
        ("Where do I volunteer?", "volunteer", "animal shelter", 19),
        ("What is my favorite restaurant?", "restaurant", "french laundry", 20),
    ]

    results = []

    for question, fact_type, expected_keyword, planted_at in test_questions:
        exchanges_ago = len(conversation) - planted_at + 1

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

                    results.append({
                        'question': question,
                        'fact_type': fact_type,
                        'exchanges_ago': exchanges_ago,
                        'remembered': remembered,
                        'response': ai_response
                    })

                    print(f"  {exchanges_ago:2d} exchanges ago: {status} - {question}")
                    if not remembered:
                        print(f"     Expected: '{expected_keyword}' in response")
                        print(f"     Got: {ai_response[:100]}...")
                else:
                    print(f"  {question} -> ❌ API ERROR (list response)")
            else:
                print(f"  {question} -> ❌ HTTP ERROR ({response.status_code})")

            time.sleep(0.5)

        except Exception as e:
            print(f"  {question} -> ❌ EXCEPTION: {e}")

    # Analyze results
    print(f"\n📊 MEMORY ANALYSIS:")
    print("="*60)

    memory_ranges = [
        ("Recent (1-5 exchanges ago)", lambda x: x <= 5),
        ("Medium (6-10 exchanges ago)", lambda x: 6 <= x <= 10),
        ("Distant (11-15 exchanges ago)", lambda x: 11 <= x <= 15),
        ("Very old (16+ exchanges ago)", lambda x: x >= 16),
    ]

    for range_name, range_filter in memory_ranges:
        range_results = [r for r in results if range_filter(r['exchanges_ago'])]
        if range_results:
            remembered_count = len([r for r in range_results if r['remembered']])
            total_count = len(range_results)
            success_rate = remembered_count / total_count * 100
            print(f"{range_name}: {remembered_count}/{total_count} ({success_rate:.1f}%)")

    # Find the memory cliff
    print(f"\n🧗 MEMORY CLIFF ANALYSIS:")
    print("="*40)

    for i in range(1, 21):
        range_results = [r for r in results if r['exchanges_ago'] == i]
        if range_results:
            remembered = range_results[0]['remembered']
            status = "✅" if remembered else "❌"
            print(f"  {i:2d} exchanges ago: {status}")

if __name__ == "__main__":
    test_extended_memory()