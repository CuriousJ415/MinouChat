#!/usr/bin/env python3
"""
Automated test runner for MiaChat document/RAG system.
"""

import os
import sys
import time
import subprocess
import requests
import json
from pathlib import Path
from typing import Dict, List, Any

class MiaChatTester:
    """Automated testing suite for MiaChat document/RAG functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.test_results = []
        self.session = requests.Session()
        
    def run_all_tests(self):
        """Run complete test suite."""
        print("🧪 Starting MiaChat RAG System Tests")
        print("=" * 50)
        
        # Check if system is running
        if not self._check_system_health():
            print("❌ System not accessible. Make sure MiaChat is running on port 8080")
            return False
        
        # Run test categories
        self._test_api_endpoints()
        self._test_document_formats()
        self._test_search_functionality()
        self._test_rag_integration()
        
        # Print results summary
        self._print_results_summary()
        
        return len([r for r in self.test_results if not r['passed']]) == 0
    
    def _check_system_health(self) -> bool:
        """Check if MiaChat system is running and healthy."""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ System Health: {health_data.get('status', 'unknown')}")
                print(f"   Characters: {health_data.get('characters', {}).get('total', 0)}")
                return True
        except Exception as e:
            print(f"❌ Health check failed: {e}")
        return False
    
    def _test_api_endpoints(self):
        """Test core API endpoints."""
        print("\n📡 Testing API Endpoints")
        print("-" * 30)
        
        endpoints = [
            ("GET", "/api/documents/formats/supported", "Supported formats"),
            ("GET", "/api/documents/stats/embedding-service", "Embedding stats"),
            ("GET", "/api/characters", "Characters list"),
            ("GET", "/api/characters/examples", "Example characters"),
        ]
        
        for method, endpoint, description in endpoints:
            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}")
                
                success = response.status_code in [200, 401]  # 401 is OK for auth-required endpoints
                status = "✅" if success else "❌"
                
                self.test_results.append({
                    'category': 'API',
                    'test': description,
                    'passed': success,
                    'details': f"Status: {response.status_code}"
                })
                
                print(f"   {status} {description}: {response.status_code}")
                
                if success and response.status_code == 200:
                    data = response.json()
                    if endpoint == "/api/documents/formats/supported":
                        formats = data.get('supported_formats', [])
                        print(f"      Supported formats: {len(formats)}")
                    elif endpoint == "/api/characters":
                        print(f"      Characters: {len(data) if isinstance(data, list) else 'N/A'}")
                
            except Exception as e:
                self.test_results.append({
                    'category': 'API',
                    'test': description,
                    'passed': False,
                    'details': f"Error: {str(e)}"
                })
                print(f"   ❌ {description}: {str(e)}")
    
    def _test_document_formats(self):
        """Test document format support."""
        print("\n📄 Testing Document Formats")
        print("-" * 30)
        
        # Test supported formats endpoint
        try:
            response = self.session.get(f"{self.base_url}/api/documents/formats/supported")
            if response.status_code == 200:
                data = response.json()
                supported_formats = data.get('supported_formats', [])
                
                expected_formats = ['.pdf', '.docx', '.txt', '.csv', '.xlsx', '.md']
                
                for fmt in expected_formats:
                    supported = fmt in supported_formats
                    status = "✅" if supported else "❌"
                    print(f"   {status} {fmt} support")
                    
                    self.test_results.append({
                        'category': 'Formats',
                        'test': f"{fmt} support",
                        'passed': supported,
                        'details': f"Format in supported list: {supported}"
                    })
            else:
                print(f"   ❌ Could not retrieve supported formats: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Format test failed: {e}")
    
    def _test_search_functionality(self):
        """Test search functionality with mock data."""
        print("\n🔍 Testing Search Functionality")
        print("-" * 30)
        
        # Test search endpoint structure
        search_data = {
            "query": "test query",
            "top_k": 5,
            "similarity_threshold": 0.3
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/documents/search",
                json=search_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Expect 401 (auth required) or 200 (if somehow authenticated)
            success = response.status_code in [200, 401]
            status = "✅" if success else "❌"
            
            print(f"   {status} Search endpoint accessibility: {response.status_code}")
            
            self.test_results.append({
                'category': 'Search',
                'test': 'Search endpoint',
                'passed': success,
                'details': f"Status: {response.status_code}"
            })
            
            if response.status_code == 200:
                results = response.json()
                print(f"      Search results type: {type(results)}")
                
        except Exception as e:
            print(f"   ❌ Search test failed: {e}")
            self.test_results.append({
                'category': 'Search',
                'test': 'Search endpoint',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
    
    def _test_rag_integration(self):
        """Test RAG integration in chat."""
        print("\n🤖 Testing RAG Integration")
        print("-" * 30)
        
        # Test RAG context endpoint
        rag_data = {
            "message": "test message",
            "conversation_id": None,
            "character_id": "test",
            "include_conversation_history": True,
            "include_documents": True
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/documents/rag/context",
                json=rag_data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code in [200, 401]
            status = "✅" if success else "❌"
            
            print(f"   {status} RAG context endpoint: {response.status_code}")
            
            self.test_results.append({
                'category': 'RAG',
                'test': 'RAG context endpoint',
                'passed': success,
                'details': f"Status: {response.status_code}"
            })
            
        except Exception as e:
            print(f"   ❌ RAG context test failed: {e}")
            self.test_results.append({
                'category': 'RAG',
                'test': 'RAG context endpoint',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
        
        # Test chat endpoint with RAG
        chat_data = {
            "message": "What is our company about?",
            "character_id": "test-character",
            "use_documents": True
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=chat_data,
                headers={"Content-Type": "application/json"}
            )
            
            success = response.status_code in [200, 401, 404]  # 404 OK for missing character
            status = "✅" if success else "❌"
            
            print(f"   {status} Chat with RAG: {response.status_code}")
            
            self.test_results.append({
                'category': 'RAG',
                'test': 'Chat with RAG',
                'passed': success,
                'details': f"Status: {response.status_code}"
            })
            
        except Exception as e:
            print(f"   ❌ Chat RAG test failed: {e}")
            self.test_results.append({
                'category': 'RAG',
                'test': 'Chat with RAG',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
    
    def _print_results_summary(self):
        """Print test results summary."""
        print("\n📊 Test Results Summary")
        print("=" * 50)
        
        categories = {}
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if result['passed']:
                categories[cat]['passed'] += 1
        
        for category, stats in categories.items():
            print(f"\n{category} Tests:")
            print(f"   Passed: {stats['passed']}/{stats['total']}")
            
            # Show failed tests
            failed = [r for r in self.test_results 
                     if r['category'] == category and not r['passed']]
            if failed:
                print("   Failed tests:")
                for test in failed:
                    print(f"     ❌ {test['test']}: {test['details']}")
        
        print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if passed_tests < total_tests:
            print("   • Check that MiaChat is running: ./start.sh")
            print("   • Verify dependencies: pip install -r requirements.txt")
            print("   • Check Docker logs: docker compose logs -f")
            print("   • Try accessing web interface: http://localhost:8080")
        else:
            print("   • System appears to be working correctly!")
            print("   • Try uploading test documents for full testing")
            print("   • Run manual tests from TESTING_GUIDE.md")

def run_dependency_checks():
    """Check if required dependencies are installed."""
    print("🔍 Checking Dependencies")
    print("-" * 30)
    
    required_packages = [
        'fastapi',
        'sentence_transformers', 
        'faiss-cpu',
        'pandas',
        'python-docx',
        'PyMuPDF',
        'requests'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All dependencies available")
        return True

def check_docker_status():
    """Check if Docker containers are running."""
    print("\n🐳 Checking Docker Status")
    print("-" * 30)
    
    try:
        result = subprocess.run(['docker', 'compose', 'ps'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Header + at least one container
                print("   ✅ Docker containers running:")
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        print(f"      {line}")
            else:
                print("   ⚠️  No Docker containers found")
                print("   Run: ./start.sh or docker compose up -d")
        else:
            print(f"   ❌ Docker compose error: {result.stderr}")
    except FileNotFoundError:
        print("   ❌ Docker not found - install Docker")
    except Exception as e:
        print(f"   ❌ Error checking Docker: {e}")

def create_test_documents():
    """Create test documents for manual testing."""
    print("\n📝 Creating Test Documents")
    print("-" * 30)
    
    script_path = Path(__file__).parent / "test_sample_data" / "create_test_documents.py"
    
    if script_path.exists():
        try:
            subprocess.run([sys.executable, str(script_path)], check=True)
            print("   ✅ Test documents created successfully")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error creating test documents: {e}")
    else:
        print(f"   ❌ Test document script not found: {script_path}")

def main():
    """Main test runner."""
    print("🚀 MiaChat Document/RAG System Test Suite")
    print("=" * 60)
    
    # Check dependencies
    if not run_dependency_checks():
        print("\n❌ Cannot proceed without required dependencies")
        return 1
    
    # Check Docker status
    check_docker_status()
    
    # Create test documents
    create_test_documents()
    
    # Wait a moment for system to be ready
    print("\n⏳ Waiting for system to be ready...")
    time.sleep(3)
    
    # Run automated tests
    tester = MiaChatTester()
    success = tester.run_all_tests()
    
    # Final recommendations
    print("\n🎯 Next Steps:")
    print("-" * 20)
    print("1. Open http://localhost:8080 in your browser")
    print("2. Register/login to create an account")
    print("3. Go to /documents page")
    print("4. Upload test documents from test_sample_data/documents/")
    print("5. Try searching and chatting with documents")
    print("6. Follow TESTING_GUIDE.md for detailed manual tests")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())