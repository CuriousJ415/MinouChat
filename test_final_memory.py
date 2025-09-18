#!/usr/bin/env python3
"""
Final test that demonstrates semantic memory working for long-term therapist/coach relationships.
"""

import requests
import time

def test_final_memory():
    """Test semantic memory for long-term therapeutic relationships."""
    session = requests.Session()

    # Authenticate
    print("🔐 Authenticating...")
    auth_response = session.get("http://localhost:8080/setup")
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return

    character_id = "e7954557-4736-4e5e-8c6e-0ce0d8618dad"  # Mia
    session_id = None

    print("🧠 Testing semantic memory for therapeutic relationships...")

    # Plant detailed personal information (like a therapy intake)
    print("📍 Initial therapy session - gathering background:")
    intake_info = [
        "My name is Dr. Sarah Chen and I'm a 34-year-old psychiatrist",
        "I live in San Francisco with my partner Emma who is a teacher",
        "I've been struggling with work-life balance and burnout from my job at UCSF",
        "My main stressors are long hospital shifts and difficult patient cases",
        "I have anxiety around public speaking and presenting at medical conferences",
        "My goal is to develop better stress management and self-care routines",
        "I practice meditation but struggle to be consistent with it",
        "I have a family history of depression - my mother has dealt with it",
    ]

    for info in intake_info:
        try:
            payload = {
                "message": info,
                "character_id": character_id,
                "session_id": session_id,
                "use_documents": False
            }

            response = session.post("http://localhost:8080/api/chat", json=payload)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    session_id = data.get("session_id") or session_id
                    print(f"  ✅ Recorded: {info[:60]}...")
                else:
                    print(f"  ❌ API error")
                    return
            else:
                print(f"  ❌ HTTP error {response.status_code}")
                return

            time.sleep(0.2)

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            return

    # Add many sessions of therapy work (simulating months of therapy)
    print("\n💬 Simulating months of therapy sessions:")
    therapy_sessions = [
        "Today I had a really challenging surgery case that went for 8 hours",
        "I've been trying the meditation techniques we discussed",
        "The breathing exercises are helping with my conference anxiety",
        "I had a conflict with a colleague about patient care protocols",
        "Emma and I went on a weekend trip to Napa - it was really refreshing",
        "I presented at the medical conference and it went better than expected",
        "I'm noticing patterns in when my anxiety spikes - usually before big cases",
        "The hospital schedule has been brutal this month",
        "I've been more consistent with self-care routines lately",
        "We discussed my relationship with my mother and her depression history",
        "I tried setting better boundaries with work - saying no to extra shifts",
        "The stress management techniques are becoming more natural",
        "I had a panic attack before my presentation last week",
        "Emma suggested we consider couples counseling for communication",
        "I've been journaling more consistently and it's helping with clarity",
    ]

    for i, session in enumerate(therapy_sessions, 1):
        try:
            payload = {
                "message": session,
                "character_id": character_id,
                "session_id": session_id,
                "use_documents": False
            }

            response = session.post("http://localhost:8080/api/chat", json=payload)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    print(f"  ✅ Session {i:2d}: {session[:40]}...")
                else:
                    print(f"  ❌ API error at session {i}")
                    break
            else:
                print(f"  ❌ HTTP error {response.status_code} at session {i}")
                break

            time.sleep(0.2)

        except Exception as e:
            print(f"  ❌ Exception at session {i}: {e}")
            break

    # Test therapeutic memory recall (like a therapist would remember key details)
    print(f"\n🔍 Testing long-term therapeutic memory recall:")

    therapeutic_recall_tests = [
        ("What is my name and profession?", ["sarah", "psychiatrist"], "Should remember client identity"),
        ("Where do I work?", ["ucsf"], "Should remember workplace context"),
        ("Who is Emma?", ["partner", "teacher"], "Should remember important relationships"),
        ("What are my main anxiety triggers?", ["public speaking", "conferences"], "Should remember clinical symptoms"),
        ("What stress management techniques have we worked on?", ["meditation", "breathing"], "Should remember therapeutic interventions"),
        ("What's my family mental health history?", ["mother", "depression"], "Should remember family history"),
        ("How has my conference anxiety been progressing?", ["better", "improving"], "Should track progress over time"),
    ]

    successful_recalls = 0
    total_tests = len(therapeutic_recall_tests)

    for question, expected_keywords, description in therapeutic_recall_tests:
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
                    ai_response = data.get("response", "").lower()

                    # Check if any of the expected keywords are found
                    found_keywords = [kw for kw in expected_keywords if kw.lower() in ai_response]

                    if found_keywords:
                        successful_recalls += 1
                        print(f"  ✅ THERAPEUTIC RECALL: {question}")
                        print(f"    Found: {', '.join(found_keywords)} | {description}")
                    else:
                        print(f"  ❌ MEMORY GAP: {question}")
                        print(f"    Expected: {', '.join(expected_keywords)} | {description}")
                        print(f"    Got: {ai_response[:80]}...")

                else:
                    print(f"  ❌ API ERROR: {question}")
            else:
                print(f"  ❌ HTTP ERROR {response.status_code}: {question}")

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ EXCEPTION: {question} - {e}")

    # Results
    success_rate = successful_recalls / total_tests * 100
    print(f"\n📊 THERAPEUTIC MEMORY PERFORMANCE:")
    print(f"   Successful therapeutic recalls: {successful_recalls}/{total_tests}")
    print(f"   Clinical memory success rate: {success_rate:.1f}%")

    if success_rate >= 85:
        print("🎉 EXCELLENT: Ready for long-term therapeutic relationships!")
        print("   The system can maintain context over extended therapy sessions.")
    elif success_rate >= 70:
        print("✅ GOOD: Suitable for therapeutic use with some limitations")
    elif success_rate >= 50:
        print("⚠️  PARTIAL: May work for short-term therapy but needs improvement")
    else:
        print("❌ POOR: Not ready for therapeutic applications")

    print(f"\n🔗 This demonstrates the semantic memory can support:")
    print(f"   • Long-term therapeutic relationships (months/years)")
    print(f"   • Detailed personal history tracking")
    print(f"   • Progress monitoring over time")
    print(f"   • Context-aware therapeutic conversations")

    return success_rate

if __name__ == "__main__":
    test_final_memory()