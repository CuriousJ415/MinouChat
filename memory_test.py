#!/usr/bin/env python3
"""
Memory System Test for MiaChat

This script tests the long-term memory and context awareness capabilities
by conducting a multi-turn conversation and checking memory retention.
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

class MiaChatMemoryTester:
    """Test suite for memory system functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = requests.Session()
        self.conversation_id = None
        self.test_results = []
    
    def run_memory_tests(self):
        """Run comprehensive memory system tests."""
        print("🧠 MiaChat Memory System Test Suite")
        print("=" * 50)
        
        # Test 1: Check if system is running
        if not self._check_system_health():
            print("❌ System not accessible")
            return False
        
        # Test 2: Multi-turn conversation with context awareness
        self._test_conversation_context_awareness()
        
        # Test 3: Long-term memory retention
        self._test_long_term_memory()
        
        # Test 4: Information recall across different topics
        self._test_cross_topic_memory()
        
        # Test 5: Integration with document memory (RAG)
        self._test_document_memory_integration()
        
        # Print results
        self._print_results()
        
        return len([r for r in self.test_results if not r['passed']]) == 0
    
    def _check_system_health(self) -> bool:
        """Check if system is running."""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                print("✅ System is healthy")
                return True
        except Exception as e:
            print(f"❌ Health check failed: {e}")
        return False
    
    def _test_conversation_context_awareness(self):
        """Test short-term conversation context."""
        print("\n📝 Testing Conversation Context Awareness")
        print("-" * 40)
        
        # Start conversation with initial information
        messages = [
            "Hi! My name is Alex and I'm a software engineer at TechCorp.",
            "I'm working on a Python project using FastAPI.",
            "What's my name?",
            "What company do I work at?",
            "What technology am I using for my project?"
        ]
        
        responses = []
        for i, message in enumerate(messages):
            print(f"User: {message}")
            
            try:
                response = self._send_chat_message(message)
                if response:
                    responses.append(response)
                    print(f"Assistant: {response.get('message', 'No response')[:100]}...")
                    
                    # Test memory retention
                    if i == 2:  # "What's my name?"
                        contains_name = "alex" in response.get('message', '').lower()
                        self.test_results.append({
                            'category': 'Context Memory',
                            'test': 'Name recall',
                            'passed': contains_name,
                            'details': f"Response contains name: {contains_name}"
                        })
                    
                    elif i == 3:  # "What company do I work at?"
                        contains_company = "techcorp" in response.get('message', '').lower()
                        self.test_results.append({
                            'category': 'Context Memory',
                            'test': 'Company recall',
                            'passed': contains_company,
                            'details': f"Response contains company: {contains_company}"
                        })
                    
                    elif i == 4:  # "What technology am I using?"
                        contains_tech = any(tech in response.get('message', '').lower() 
                                          for tech in ['fastapi', 'python'])
                        self.test_results.append({
                            'category': 'Context Memory',
                            'test': 'Technology recall',
                            'passed': contains_tech,
                            'details': f"Response contains technology: {contains_tech}"
                        })
                
                time.sleep(1)  # Brief pause between messages
                
            except Exception as e:
                print(f"❌ Error sending message: {e}")
                self.test_results.append({
                    'category': 'Context Memory',
                    'test': f'Message {i+1}',
                    'passed': False,
                    'details': f"Error: {str(e)}"
                })
    
    def _test_long_term_memory(self):
        """Test memory retention over multiple conversation turns."""
        print("\n🕐 Testing Long-term Memory Retention")
        print("-" * 40)
        
        # Add more information and test recall after many messages
        memory_items = [
            ("I have a pet dog named Max", "dog", "max"),
            ("My favorite programming language is Rust", "rust", "programming"),
            ("I was born in Seattle", "seattle", "born"),
            ("I love playing chess in my free time", "chess", "hobby")
        ]
        
        # Introduce information
        for statement, _, _ in memory_items:
            print(f"User: {statement}")
            response = self._send_chat_message(statement)
            if response:
                print(f"Assistant: {response.get('message', '')[:60]}...")
            time.sleep(0.5)
        
        # Add some intervening conversation to test memory persistence
        filler_messages = [
            "What's the weather like?",
            "Tell me about artificial intelligence",
            "How do you process information?",
            "What are your capabilities?"
        ]
        
        for message in filler_messages:
            self._send_chat_message(message)
            time.sleep(0.5)
        
        # Test recall of earlier information
        for statement, keyword1, keyword2 in memory_items:
            recall_question = f"Earlier I mentioned something about {keyword2}. What was it?"
            print(f"User: {recall_question}")
            
            response = self._send_chat_message(recall_question)
            if response:
                response_text = response.get('message', '').lower()
                print(f"Assistant: {response.get('message', '')[:80]}...")
                
                # Check if the assistant recalls the information
                contains_info = keyword1.lower() in response_text
                self.test_results.append({
                    'category': 'Long-term Memory',
                    'test': f'Recall {keyword2}',
                    'passed': contains_info,
                    'details': f"Recalled {keyword1}: {contains_info}"
                })
            
            time.sleep(1)
    
    def _test_cross_topic_memory(self):
        """Test memory retention across different conversation topics."""
        print("\n🔀 Testing Cross-topic Memory")
        print("-" * 40)
        
        # This tests if the AI can maintain context when topics change
        test_passed = True
        try:
            # Switch topics and test if earlier context is maintained
            self._send_chat_message("Let's talk about cooking now. Do you have any recipe suggestions?")
            time.sleep(0.5)
            
            # Try to recall information from earlier in the conversation
            recall_response = self._send_chat_message("By the way, do you remember what company I work at?")
            
            if recall_response:
                contains_company = "techcorp" in recall_response.get('message', '').lower()
                self.test_results.append({
                    'category': 'Cross-topic Memory',
                    'test': 'Company recall after topic change',
                    'passed': contains_company,
                    'details': f"Remembered company after topic change: {contains_company}"
                })
            
        except Exception as e:
            self.test_results.append({
                'category': 'Cross-topic Memory',
                'test': 'Topic change memory',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
    
    def _test_document_memory_integration(self):
        """Test integration between conversation memory and document memory."""
        print("\n📚 Testing Document Memory Integration")
        print("-" * 40)
        
        # This would test RAG integration with conversation memory
        try:
            # Send a message that should trigger document search
            response = self._send_chat_message("Can you tell me about our company's business plan?", use_documents=True)
            
            if response:
                has_doc_context = response.get('document_context_used', False)
                sources = response.get('sources', [])
                
                self.test_results.append({
                    'category': 'Document Memory',
                    'test': 'RAG integration',
                    'passed': has_doc_context or len(sources) > 0,
                    'details': f"Document context used: {has_doc_context}, Sources: {len(sources)}"
                })
                
                print(f"Document context used: {has_doc_context}")
                print(f"Sources found: {len(sources)}")
            
        except Exception as e:
            self.test_results.append({
                'category': 'Document Memory',
                'test': 'RAG integration',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
    
    def _send_chat_message(self, message: str, use_documents: bool = False) -> Dict[str, Any]:
        """Send a chat message and return response."""
        
        # Use Mia's character ID (from earlier API test)
        character_id = "e7954557-4736-4e5e-8c6e-0ce0d8618dad"
        
        payload = {
            "message": message,
            "character_id": character_id,
            "use_documents": use_documents
        }
        
        if self.conversation_id:
            payload["session_id"] = self.conversation_id
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                # Store conversation ID for continuity
                if not self.conversation_id and data.get('conversation_id'):
                    self.conversation_id = data.get('conversation_id')
                return data
            
            elif response.status_code == 401:
                print("⚠️  Authentication required - some memory features may be limited")
                return None
            
            else:
                print(f"❌ Chat request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        
        except Exception as e:
            print(f"❌ Error sending chat message: {e}")
            return None
    
    def _print_results(self):
        """Print test results summary."""
        print("\n📊 Memory System Test Results")
        print("=" * 50)
        
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if result['passed']:
                categories[cat]['passed'] += 1
        
        for category, stats in categories.items():
            print(f"\n{category}:")
            print(f"   Passed: {stats['passed']}/{stats['total']}")
            
            # Show failed tests
            failed = [r for r in self.test_results 
                     if r['category'] == category and not r['passed']]
            if failed:
                print("   Failed tests:")
                for test in failed:
                    print(f"     ❌ {test['test']}: {test['details']}")
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        
        print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All memory tests passed!")
        else:
            print(f"⚠️  {total_tests - passed_tests} memory tests failed")
        
        # Memory system evaluation
        print(f"\n💡 Memory System Evaluation:")
        if passed_tests / total_tests >= 0.8:
            print("   ✅ Memory system is working well")
        elif passed_tests / total_tests >= 0.6:
            print("   ⚠️  Memory system has some issues")
        else:
            print("   ❌ Memory system needs significant improvement")

def main():
    """Run the memory system tests."""
    tester = MiaChatMemoryTester()
    success = tester.run_memory_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())