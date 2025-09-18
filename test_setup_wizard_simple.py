#!/usr/bin/env python3
"""
Simple automated test for the MiaChat Setup Wizard workflow.

This script tests the key functionality without complex pytest setup.
Can be run inside the Docker container where all dependencies are available.
"""

import requests
import json
import time
import sys

class SetupWizardTester:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def log(self, test_name, success, message=""):
        """Log test results."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append({"test": test_name, "success": success, "message": message})
        print(f"{status} {test_name}: {message}")
    
    def test_favicon(self):
        """Test that favicon endpoint works."""
        try:
            response = self.session.get(f"{self.base_url}/favicon.ico")
            success = response.status_code == 200 and response.headers.get("content-type") == "image/x-icon"
            self.log("Favicon endpoint", success, f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log("Favicon endpoint", False, f"Error: {e}")
            return False
    
    def test_setup_page_loads(self):
        """Test that setup page loads and creates session."""
        try:
            response = self.session.get(f"{self.base_url}/setup")
            success = response.status_code == 200 and b"Setup Wizard" in response.content
            has_session = 'session' in response.cookies
            
            self.log("Setup page loads", success, f"Status: {response.status_code}, Session: {has_session}")
            return success and has_session
        except Exception as e:
            self.log("Setup page loads", False, f"Error: {e}")
            return False
    
    def test_system_assessment(self):
        """Test system assessment endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/api/setup/assessment")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                required_fields = ["timestamp", "overall_status", "providers", "personas", "privacy_score"]
                has_all_fields = all(field in data for field in required_fields)
                
                providers = [p["provider"] for p in data.get("providers", [])]
                expected_providers = ["ollama", "openai", "anthropic", "openrouter"]
                has_providers = all(p in providers for p in expected_providers)
                
                success = has_all_fields and has_providers
                
                self.log("System assessment", success, 
                        f"Fields: {has_all_fields}, Providers: {has_providers} {providers}")
                return success
            else:
                self.log("System assessment", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log("System assessment", False, f"Error: {e}")
            return False
    
    def test_api_key_validation(self):
        """Test API key validation functionality."""
        try:
            # Test with invalid key
            response = self.session.post(f"{self.base_url}/api/setup/test-api-key", json={
                "provider": "openai",
                "api_key": "invalid_key"
            })
            
            success = response.status_code == 200
            if success:
                data = response.json()
                success = "success" in data and data["success"] is False
            
            self.log("API key validation", success, f"Invalid key rejected: {success}")
            
            # Test with empty key
            response = self.session.post(f"{self.base_url}/api/setup/test-api-key", json={
                "provider": "openai",
                "api_key": ""
            })
            
            empty_key_handled = response.status_code == 200
            if empty_key_handled:
                data = response.json()
                empty_key_handled = data.get("success") is False and "required" in data.get("message", "")
            
            self.log("API key validation - empty key", empty_key_handled, 
                    f"Empty key rejected properly: {empty_key_handled}")
            
            return success and empty_key_handled
        except Exception as e:
            self.log("API key validation", False, f"Error: {e}")
            return False
    
    def test_model_assignment_without_auth(self):
        """Test that model assignment requires authentication."""
        try:
            # Create a new session without visiting setup page
            new_session = requests.Session()
            response = new_session.post(f"{self.base_url}/api/setup/assign-models", json={
                "assignments": [],
                "preference": "balanced"
            })
            
            # Should require authentication
            success = response.status_code == 401
            self.log("Model assignment auth required", success, 
                    f"Status: {response.status_code} (should be 401)")
            return success
        except Exception as e:
            self.log("Model assignment auth required", False, f"Error: {e}")
            return False
    
    def test_model_assignment_with_auth(self):
        """Test model assignment with proper authentication."""
        try:
            # Use session that visited setup page (has auth)
            response = self.session.post(f"{self.base_url}/api/setup/assign-models", json={
                "assignments": [],
                "preference": "balanced"
            })
            
            success = response.status_code == 200
            if success:
                data = response.json()
                success = data.get("success") is True and "updated_personas" in data
            
            self.log("Model assignment with auth", success, 
                    f"Status: {response.status_code}, Success: {success}")
            return success
        except Exception as e:
            self.log("Model assignment with auth", False, f"Error: {e}")
            return False
    
    def test_model_discovery(self):
        """Test model discovery endpoints."""
        try:
            # Test default privacy mode
            response = self.session.get(f"{self.base_url}/api/models")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                has_ollama = "ollama" in data and len(data["ollama"]) > 0
                
                # Test cloud_allowed mode
                response_cloud = self.session.get(f"{self.base_url}/api/models?privacy_mode=cloud_allowed")
                cloud_success = response_cloud.status_code == 200
                
                if cloud_success:
                    cloud_data = response_cloud.json()
                    expected_providers = ["ollama", "openai", "anthropic", "openrouter"]
                    has_all_providers = all(p in cloud_data for p in expected_providers)
                    has_models = all(len(cloud_data[p]) > 0 for p in expected_providers)
                    
                    success = has_ollama and has_all_providers and has_models
                    
                    self.log("Model discovery", success, 
                            f"Ollama: {has_ollama}, Providers: {has_all_providers}, Models: {has_models}")
                else:
                    self.log("Model discovery", False, f"Cloud mode failed: {response_cloud.status_code}")
                    success = False
            else:
                self.log("Model discovery", False, f"Status: {response.status_code}")
            
            return success
        except Exception as e:
            self.log("Model discovery", False, f"Error: {e}")
            return False
    
    def test_complete_workflow(self):
        """Test complete setup wizard workflow."""
        try:
            # Step 1: Visit setup page
            setup_response = self.session.get(f"{self.base_url}/setup")
            if setup_response.status_code != 200:
                self.log("Complete workflow", False, "Setup page failed")
                return False
            
            # Step 2: Get assessment
            assessment_response = self.session.get(f"{self.base_url}/api/setup/assessment")
            if assessment_response.status_code != 200:
                self.log("Complete workflow", False, "Assessment failed")
                return False
            
            assessment = assessment_response.json()
            
            # Step 3: Test API key (optional)
            api_key_response = self.session.post(f"{self.base_url}/api/setup/test-api-key", json={
                "provider": "openai",
                "api_key": "invalid_test"
            })
            if api_key_response.status_code != 200:
                self.log("Complete workflow", False, "API key test failed")
                return False
            
            # Step 4: Assign models
            if assessment.get("personas"):
                assignments = []
                for persona in assessment["personas"][:2]:  # First 2 personas
                    assignments.append({
                        "persona_id": persona["persona_id"],
                        "provider": "ollama",
                        "model": "llama3.1:latest"
                    })
                
                assign_response = self.session.post(f"{self.base_url}/api/setup/assign-models", json={
                    "assignments": assignments,
                    "preference": "privacy"
                })
                
                if assign_response.status_code != 200:
                    self.log("Complete workflow", False, "Model assignment failed")
                    return False
                
                assign_data = assign_response.json()
                if not assign_data.get("success"):
                    self.log("Complete workflow", False, "Assignment not successful")
                    return False
            
            # Step 5: Verify completion
            check_response = self.session.get(f"{self.base_url}/api/setup/check-first-run")
            success = check_response.status_code == 200
            
            self.log("Complete workflow", success, "All steps completed successfully")
            return success
            
        except Exception as e:
            self.log("Complete workflow", False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests and return summary."""
        print("🚀 Starting MiaChat Setup Wizard Tests\n")
        
        tests = [
            self.test_favicon,
            self.test_setup_page_loads,
            self.test_system_assessment,
            self.test_api_key_validation,
            self.test_model_assignment_without_auth,
            self.test_model_assignment_with_auth,
            self.test_model_discovery,
            self.test_complete_workflow
        ]
        
        for test in tests:
            test()
            time.sleep(0.5)  # Brief pause between tests
        
        print("\n📊 Test Summary:")
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print(f"Passed: {passed}/{total}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")
            return False

def main():
    """Main function to run tests."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8080"
    
    print(f"Testing MiaChat Setup Wizard at: {base_url}")
    
    tester = SetupWizardTester(base_url)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()