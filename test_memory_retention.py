#!/usr/bin/env python3
"""
Memory Retention Test Suite for MiaChat

Tests short-term, medium-term, and long-term memory capabilities by conducting
a scripted conversation and testing recall at different intervals.
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class MemoryFact:
    """Represents a fact to be remembered during conversation."""
    fact_type: str
    key: str
    value: str
    exchange_number: int
    test_question: str
    expected_keywords: List[str]

@dataclass
class MemoryTestResult:
    """Results of a memory test."""
    fact: MemoryFact
    recall_successful: bool
    response: str
    confidence_score: float
    exchanges_elapsed: int

class MemoryTester:
    def __init__(self, base_url="http://localhost:8080", character_id="mia"):
        self.base_url = base_url
        self.character_id = character_id
        self.session = requests.Session()
        self.session_id = None
        self.exchange_count = 0
        self.conversation_log = []
        self.test_facts = []
        self.results = []

    def setup_test_facts(self):
        """Define facts to plant and test throughout the conversation."""
        self.test_facts = [
            # Short-term memory (last 1-3 exchanges)
            MemoryFact(
                fact_type="short_term",
                key="favorite_color",
                value="emerald green",
                exchange_number=18,
                test_question="What did I say my favorite color was?",
                expected_keywords=["emerald", "green"]
            ),
            MemoryFact(
                fact_type="short_term",
                key="lunch_plan",
                value="sushi at Nobu",
                exchange_number=17,
                test_question="Where did I say I'm having lunch today?",
                expected_keywords=["sushi", "nobu"]
            ),

            # Medium-term memory (4-10 exchanges back)
            MemoryFact(
                fact_type="medium_term",
                key="pet_name",
                value="Captain Whiskers",
                exchange_number=12,
                test_question="What is my cat's name?",
                expected_keywords=["captain", "whiskers"]
            ),
            MemoryFact(
                fact_type="medium_term",
                key="hobby",
                value="vintage motorcycle restoration",
                exchange_number=10,
                test_question="What hobby did I mention I enjoy?",
                expected_keywords=["vintage", "motorcycle", "restoration"]
            ),
            MemoryFact(
                fact_type="medium_term",
                key="birthday",
                value="March 15th",
                exchange_number=8,
                test_question="When is my birthday?",
                expected_keywords=["march", "15"]
            ),

            # Long-term memory (11+ exchanges back)
            MemoryFact(
                fact_type="long_term",
                key="name",
                value="Alex Rodriguez",
                exchange_number=2,
                test_question="What is my name?",
                expected_keywords=["alex", "rodriguez"]
            ),
            MemoryFact(
                fact_type="long_term",
                key="city",
                value="Portland, Oregon",
                exchange_number=3,
                test_question="What city do I live in?",
                expected_keywords=["portland", "oregon"]
            ),
            MemoryFact(
                fact_type="long_term",
                key="profession",
                value="software architect",
                exchange_number=4,
                test_question="What is my profession?",
                expected_keywords=["software", "architect"]
            ),
            MemoryFact(
                fact_type="long_term",
                key="spouse",
                value="Emma",
                exchange_number=5,
                test_question="What is my spouse's name?",
                expected_keywords=["emma"]
            ),
            MemoryFact(
                fact_type="long_term",
                key="company",
                value="TechFlow Solutions",
                exchange_number=6,
                test_question="What company do I work for?",
                expected_keywords=["techflow", "solutions"]
            )
        ]

    def authenticate(self):
        """Authenticate by visiting the setup page to create a session."""
        try:
            response = self.session.get(f"{self.base_url}/setup")
            if response.status_code == 200:
                print("✅ Authentication successful via setup page")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def send_message(self, message: str) -> str:
        """Send a message to the AI and get response."""
        try:
            payload = {
                "message": message,
                "character_id": self.character_id,
                "session_id": self.session_id,
                "use_documents": False
            }

            response = self.session.post(f"{self.base_url}/api/chat", json=payload)

            # Handle both dictionary and list response formats
            if response.status_code == 200:
                data = response.json()

                # Handle normal response format
                if isinstance(data, dict):
                    ai_response = data.get("response", "")
                    # Store session ID for continuity
                    if not self.session_id:
                        self.session_id = data.get("session_id")
                else:
                    print(f"DEBUG: Unexpected response format: {type(data)}")
                    print(f"DEBUG: Response content: {data}")
                    # Try to handle list format if it contains error information
                    if isinstance(data, list) and len(data) >= 2:
                        if isinstance(data[0], dict) and "error" in data[0]:
                            print(f"API Error in response: {data[0]['error']}")
                            return ""
                    return ""
            else:
                # Handle error responses
                try:
                    error_data = response.json()
                    if isinstance(error_data, list) and len(error_data) >= 2:
                        error_msg = error_data[0].get("error", "Unknown error")
                        print(f"API Error: {error_msg} (status: {error_data[1]})")
                    else:
                        print(f"API Error: {response.status_code} - {error_data}")
                except:
                    print(f"API Error: {response.status_code} - {response.text}")
                return ""

            self.exchange_count += 1
            self.conversation_log.append({
                "exchange": self.exchange_count,
                "user": message,
                "assistant": ai_response
            })

            print(f"Exchange {self.exchange_count}:")
            print(f"User: {message}")
            print(f"Assistant: {ai_response[:100]}{'...' if len(ai_response) > 100 else ''}")
            print()

            return ai_response

        except Exception as e:
            print(f"Error sending message: {e}")
            return ""

    def conduct_conversation(self):
        """Conduct a scripted conversation that plants facts to test."""
        conversation_script = [
            "Hello! I'd like to get to know you better and see how well you remember our conversation.",
            "My name is Alex Rodriguez. I'm excited to chat with you!",
            "I live in Portland, Oregon. It's a beautiful city with great coffee shops.",
            "I work as a software architect. I've been in tech for about 10 years.",
            "I'm married to my wonderful spouse Emma. We've been together for 5 years.",
            "I work for a company called TechFlow Solutions. We build enterprise software.",
            "What I love about my job is solving complex architectural challenges.",
            "My birthday is coming up on March 15th. I'm planning a small celebration.",
            "Do you have any suggestions for birthday activities?",
            "One of my hobbies is vintage motorcycle restoration. I'm working on a 1973 Honda CB750 right now.",
            "It's a time-consuming hobby but very rewarding when you get an old bike running again.",
            "I also have a cat named Captain Whiskers. He's a Maine Coon and quite the character.",
            "Captain Whiskers likes to supervise my motorcycle work from his perch on the workbench.",
            "Speaking of work, I have a big presentation coming up next week.",
            "The presentation is about microservices architecture for our new client.",
            "I should probably start preparing the slides soon.",
            "I'm thinking of having lunch at Nobu today. Their sushi is incredible.",
            "By the way, my favorite color is emerald green. I just thought I'd mention that.",
            "Now I'd like to test your memory. Let's see how well you remember our conversation."
        ]

        print("🧠 Starting Memory Retention Test\n")
        print("Phase 1: Conducting scripted conversation to plant facts...\n")

        for i, message in enumerate(conversation_script, 1):
            self.send_message(message)
            time.sleep(1)  # Brief pause between messages

    def test_memory_recall(self):
        """Test recall of planted facts."""
        print("\n" + "="*60)
        print("Phase 2: Testing memory recall...")
        print("="*60 + "\n")

        # Sort facts by exchange number for testing in order
        test_order = sorted(self.test_facts, key=lambda x: x.exchange_number)

        for fact in test_order:
            exchanges_elapsed = self.exchange_count - fact.exchange_number

            print(f"Testing {fact.fact_type} memory (planted {exchanges_elapsed} exchanges ago):")
            print(f"Question: {fact.test_question}")

            response = self.send_message(fact.test_question)

            # Analyze response for expected keywords
            response_lower = response.lower()
            keywords_found = [kw for kw in fact.expected_keywords if kw in response_lower]
            recall_successful = len(keywords_found) > 0
            confidence_score = len(keywords_found) / len(fact.expected_keywords)

            result = MemoryTestResult(
                fact=fact,
                recall_successful=recall_successful,
                response=response,
                confidence_score=confidence_score,
                exchanges_elapsed=exchanges_elapsed
            )

            self.results.append(result)

            status = "✅ RECALLED" if recall_successful else "❌ FORGOTTEN"
            print(f"Result: {status} (confidence: {confidence_score:.2f})")
            print(f"Keywords found: {keywords_found}")
            print()

            time.sleep(2)  # Pause between tests

    def analyze_results(self):
        """Analyze and report test results."""
        print("\n" + "="*60)
        print("Phase 3: Memory Analysis Report")
        print("="*60 + "\n")

        # Group results by memory type
        short_term = [r for r in self.results if r.fact.fact_type == "short_term"]
        medium_term = [r for r in self.results if r.fact.fact_type == "medium_term"]
        long_term = [r for r in self.results if r.fact.fact_type == "long_term"]

        def analyze_group(results: List[MemoryTestResult], memory_type: str):
            if not results:
                return

            total = len(results)
            successful = len([r for r in results if r.recall_successful])
            avg_confidence = sum(r.confidence_score for r in results) / total
            avg_elapsed = sum(r.exchanges_elapsed for r in results) / total

            print(f"📊 {memory_type.upper()} MEMORY ({avg_elapsed:.1f} exchanges ago on average)")
            print(f"   Success Rate: {successful}/{total} ({successful/total*100:.1f}%)")
            print(f"   Average Confidence: {avg_confidence:.2f}")

            for result in results:
                status = "✅" if result.recall_successful else "❌"
                print(f"   {status} {result.fact.key}: {result.fact.value} "
                      f"({result.exchanges_elapsed} exchanges ago)")
            print()

        analyze_group(short_term, "short-term")
        analyze_group(medium_term, "medium-term")
        analyze_group(long_term, "long-term")

        # Overall statistics
        total_tests = len(self.results)
        total_successful = len([r for r in self.results if r.recall_successful])
        overall_success_rate = total_successful / total_tests if total_tests > 0 else 0

        print(f"🎯 OVERALL PERFORMANCE")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful Recalls: {total_successful}")
        print(f"   Overall Success Rate: {overall_success_rate*100:.1f}%")

        # Memory degradation analysis
        print(f"\n📉 MEMORY DEGRADATION ANALYSIS")
        for result in sorted(self.results, key=lambda x: x.exchanges_elapsed):
            print(f"   {result.exchanges_elapsed:2d} exchanges ago: "
                  f"{'✅' if result.recall_successful else '❌'} "
                  f"{result.fact.key} (confidence: {result.confidence_score:.2f})")

        return {
            "total_tests": total_tests,
            "successful_recalls": total_successful,
            "success_rate": overall_success_rate,
            "short_term_success": len([r for r in short_term if r.recall_successful]) / len(short_term) if short_term else 0,
            "medium_term_success": len([r for r in medium_term if r.recall_successful]) / len(medium_term) if medium_term else 0,
            "long_term_success": len([r for r in long_term if r.recall_successful]) / len(long_term) if long_term else 0
        }

    def save_detailed_report(self, filename="memory_test_report.json"):
        """Save detailed test report to file."""
        report = {
            "test_metadata": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "character_id": self.character_id,
                "session_id": self.session_id,
                "total_exchanges": self.exchange_count
            },
            "conversation_log": self.conversation_log,
            "test_facts": [
                {
                    "fact_type": f.fact_type,
                    "key": f.key,
                    "value": f.value,
                    "exchange_number": f.exchange_number,
                    "test_question": f.test_question,
                    "expected_keywords": f.expected_keywords
                } for f in self.test_facts
            ],
            "results": [
                {
                    "fact_key": r.fact.key,
                    "fact_type": r.fact.fact_type,
                    "recall_successful": r.recall_successful,
                    "confidence_score": r.confidence_score,
                    "exchanges_elapsed": r.exchanges_elapsed,
                    "response": r.response
                } for r in self.results
            ]
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n💾 Detailed report saved to: {filename}")

    def run_full_test(self):
        """Run the complete memory test suite."""
        # Authenticate first
        if not self.authenticate():
            raise Exception("Authentication failed - cannot proceed with test")

        self.setup_test_facts()
        self.conduct_conversation()
        self.test_memory_recall()
        stats = self.analyze_results()
        self.save_detailed_report()

        return stats

def main():
    """Main function to run memory tests."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8080"

    if len(sys.argv) > 2:
        character_id = sys.argv[2]
    else:
        character_id = "mia"

    print(f"🧠 Memory Retention Test Suite")
    print(f"Testing: {base_url} with character: {character_id}")
    print(f"{'='*60}\n")

    tester = MemoryTester(base_url, character_id)

    try:
        stats = tester.run_full_test()

        print(f"\n🏁 TEST COMPLETE")
        print(f"Overall Success Rate: {stats['success_rate']*100:.1f}%")

        if stats['success_rate'] < 0.5:
            print("⚠️  WARNING: Memory retention is below 50%")
            print("   Consider increasing context window or implementing better memory management")
        elif stats['success_rate'] < 0.8:
            print("⚠️  NOTICE: Memory retention could be improved")
            print("   Some long-term memories are being lost")
        else:
            print("🎉 EXCELLENT: Memory retention is performing well!")

        return 0 if stats['success_rate'] >= 0.8 else 1

    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())