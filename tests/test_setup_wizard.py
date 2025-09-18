"""
Automated tests for the MiaChat Setup Wizard workflow.

Tests the complete setup wizard flow including:
- System assessment
- API key testing 
- Model assignment
- Authorization handling
- Session management
"""

import pytest
import os
import json
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the FastAPI app and dependencies
import sys
sys.path.append('/Users/jasonnau/projects/MiaChat/src')

from miachat.api.main import app
from miachat.api.core.models import Base, User
from miachat.api.core.database import get_db

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_setup_wizard.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency for testing
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def test_db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def authenticated_client(client):
    """Create an authenticated client by visiting setup page first."""
    # Visit setup page to trigger automatic user creation and session
    response = client.get("/setup")
    assert response.status_code == 200
    return client

class TestSetupWizardAuthentication:
    """Test setup wizard authentication and session management."""
    
    def test_setup_page_loads_without_auth(self, client):
        """Test that setup page loads for unauthenticated users."""
        response = client.get("/setup")
        assert response.status_code == 200
        assert b"Setup Wizard" in response.content
        assert b"MiaChat" in response.content
    
    def test_setup_creates_user_session(self, client):
        """Test that visiting setup page creates a user session."""
        # First request should create setup user and session
        response = client.get("/setup")
        assert response.status_code == 200
        
        # Session cookies should be set
        assert 'session' in [cookie.name for cookie in client.cookies]
    
    def test_setup_user_created_in_database(self, test_db, client):
        """Test that setup user is created in database."""
        # Visit setup page to trigger user creation
        response = client.get("/setup")
        assert response.status_code == 200
        
        # Check that setup user exists in database
        db = TestingSessionLocal()
        setup_user = db.query(User).filter(User.username == "setup_user").first()
        assert setup_user is not None
        assert setup_user.email == "setup@miachat.local"
        db.close()

class TestSetupAssessment:
    """Test setup system assessment functionality."""
    
    def test_assessment_endpoint_no_auth_required(self, client):
        """Test that assessment endpoint works without authentication."""
        response = client.get("/api/setup/assessment")
        assert response.status_code == 200
        
        data = response.json()
        assert "timestamp" in data
        assert "overall_status" in data
        assert "providers" in data
        assert "personas" in data
        assert "privacy_score" in data
    
    def test_assessment_contains_expected_providers(self, client):
        """Test that assessment includes expected providers."""
        response = client.get("/api/setup/assessment")
        assert response.status_code == 200
        
        data = response.json()
        provider_names = [p["provider"] for p in data["providers"]]
        
        expected_providers = ["ollama", "openai", "anthropic", "openrouter"]
        for provider in expected_providers:
            assert provider in provider_names
    
    def test_assessment_includes_personas(self, client):
        """Test that assessment includes persona information."""
        response = client.get("/api/setup/assessment")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["personas"]) > 0
        
        # Check persona structure
        persona = data["personas"][0]
        assert "persona_name" in persona
        assert "persona_id" in persona
        assert "status" in persona

class TestApiKeyTesting:
    """Test API key testing functionality."""
    
    def test_api_key_test_endpoint_exists(self, client):
        """Test that API key test endpoint exists."""
        response = client.post("/api/setup/test-api-key", json={
            "provider": "openai",
            "api_key": "invalid_key"
        })
        # Should not be 404
        assert response.status_code != 404
    
    def test_api_key_validation_with_invalid_key(self, client):
        """Test API key validation with invalid key."""
        response = client.post("/api/setup/test-api-key", json={
            "provider": "openai", 
            "api_key": "sk-invalid123"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is False
        assert "message" in data
    
    def test_api_key_validation_empty_key(self, client):
        """Test API key validation with empty key."""
        response = client.post("/api/setup/test-api-key", json={
            "provider": "openai",
            "api_key": ""
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert "required" in data["message"]
    
    def test_api_key_validation_unknown_provider(self, client):
        """Test API key validation with unknown provider."""
        response = client.post("/api/setup/test-api-key", json={
            "provider": "unknown_provider",
            "api_key": "test_key"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert "Unknown provider" in data["message"]

class TestModelAssignment:
    """Test model assignment functionality."""
    
    def test_assign_models_requires_auth(self, client):
        """Test that assign-models endpoint requires authentication."""
        response = client.post("/api/setup/assign-models", json={
            "assignments": [],
            "preference": "balanced"
        })
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_assign_models_works_with_setup_session(self, authenticated_client):
        """Test that assign-models works with setup session."""
        response = authenticated_client.post("/api/setup/assign-models", json={
            "assignments": [],
            "preference": "balanced"
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "updated_personas" in data
    
    def test_assign_models_with_valid_assignments(self, authenticated_client, test_db):
        """Test model assignment with valid persona assignments."""
        # First get available personas
        response = authenticated_client.get("/api/setup/assessment")
        assessment = response.json()
        
        if assessment["personas"]:
            persona = assessment["personas"][0]
            
            response = authenticated_client.post("/api/setup/assign-models", json={
                "assignments": [{
                    "persona_id": persona["persona_id"],
                    "provider": "ollama",
                    "model": "llama3.1:latest"
                }],
                "preference": "privacy"
            })
            assert response.status_code == 200
            
            data = response.json()
            assert data["success"] is True
            assert len(data["updated_personas"]) == 1
    
    def test_assign_models_with_invalid_persona_id(self, authenticated_client):
        """Test model assignment with invalid persona ID."""
        response = authenticated_client.post("/api/setup/assign-models", json={
            "assignments": [{
                "persona_id": "invalid_id",
                "provider": "ollama", 
                "model": "llama3.1:latest"
            }],
            "preference": "balanced"
        })
        assert response.status_code == 200
        
        data = response.json()
        # Should succeed but show error for invalid persona
        assert data["success"] is True
        assert any(p.get("status") == "error" for p in data["updated_personas"])

class TestSetupUtilityEndpoints:
    """Test setup utility endpoints."""
    
    def test_check_first_run_endpoint(self, client):
        """Test check first run endpoint."""
        response = client.get("/api/setup/check-first-run")
        assert response.status_code == 200
        
        data = response.json()
        assert "first_run" in data
        assert "overall_status" in data
        assert isinstance(data["first_run"], bool)
    
    def test_initialize_characters_requires_auth(self, client):
        """Test that initialize-characters requires authentication."""
        response = client.post("/api/setup/initialize-characters")
        assert response.status_code == 401
    
    def test_initialize_characters_with_auth(self, authenticated_client):
        """Test character initialization with authentication."""
        response = authenticated_client.post("/api/setup/initialize-characters")
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert "characters" in data

class TestModelDiscovery:
    """Test model discovery functionality."""
    
    def test_models_endpoint_default_privacy(self, client):
        """Test models endpoint with default privacy mode."""
        response = client.get("/api/models")
        assert response.status_code == 200
        
        data = response.json()
        assert "ollama" in data
        assert isinstance(data["ollama"], list)
    
    def test_models_endpoint_cloud_allowed(self, client):
        """Test models endpoint with cloud_allowed privacy mode."""
        response = client.get("/api/models?privacy_mode=cloud_allowed")
        assert response.status_code == 200
        
        data = response.json()
        assert "ollama" in data
        assert "openai" in data
        assert "anthropic" in data
        assert "openrouter" in data
        
        # Should have models for each provider
        for provider in ["ollama", "openai", "anthropic", "openrouter"]:
            assert len(data[provider]) > 0
    
    def test_models_endpoint_local_only(self, client):
        """Test models endpoint with local_only privacy mode."""
        response = client.get("/api/models?privacy_mode=local_only")
        assert response.status_code == 200
        
        data = response.json()
        assert "ollama" in data
        # Should still include cloud providers but with static lists
        assert "openai" in data
        assert "anthropic" in data

class TestFaviconAndAssets:
    """Test favicon and static asset handling."""
    
    def test_favicon_endpoint(self, client):
        """Test that favicon endpoint works."""
        response = client.get("/favicon.ico")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/x-icon"
        assert len(response.content) > 0

class TestSetupWizardWorkflow:
    """Test complete setup wizard workflow end-to-end."""
    
    def test_complete_setup_workflow(self, client, test_db):
        """Test the complete setup wizard workflow."""
        # Step 1: Load setup page (creates session)
        response = client.get("/setup")
        assert response.status_code == 200
        
        # Step 2: Get system assessment
        response = client.get("/api/setup/assessment")
        assert response.status_code == 200
        assessment = response.json()
        
        # Step 3: Test an API key (simulate)
        response = client.post("/api/setup/test-api-key", json={
            "provider": "openai",
            "api_key": "invalid_key"
        })
        assert response.status_code == 200
        
        # Step 4: Assign models to personas
        if assessment["personas"]:
            assignments = []
            for persona in assessment["personas"][:2]:  # Take first 2 personas
                assignments.append({
                    "persona_id": persona["persona_id"],
                    "provider": "ollama",
                    "model": "llama3.1:latest"
                })
            
            response = client.post("/api/setup/assign-models", json={
                "assignments": assignments,
                "preference": "privacy"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
        
        # Step 5: Verify setup completion
        response = client.get("/api/setup/check-first-run")
        assert response.status_code == 200
    
    def test_privacy_mode_affects_model_availability(self, client):
        """Test that privacy mode affects available models in setup."""
        # Test local_only mode
        response = client.get("/api/models?privacy_mode=local_only")
        local_data = response.json()
        
        # Test cloud_allowed mode  
        response = client.get("/api/models?privacy_mode=cloud_allowed")
        cloud_data = response.json()
        
        # Both should have ollama models
        assert "ollama" in local_data
        assert "ollama" in cloud_data
        
        # Cloud allowed should have more comprehensive lists
        assert len(cloud_data["openai"]) >= len(local_data["openai"])
        assert len(cloud_data["anthropic"]) >= len(local_data["anthropic"])

class TestErrorHandling:
    """Test error handling in setup wizard."""
    
    def test_malformed_api_key_request(self, client):
        """Test handling of malformed API key test request."""
        response = client.post("/api/setup/test-api-key", json={
            "provider": "openai"
            # Missing api_key field
        })
        assert response.status_code == 422  # Validation error
    
    def test_malformed_assignment_request(self, authenticated_client):
        """Test handling of malformed assignment request."""
        response = authenticated_client.post("/api/setup/assign-models", json={
            "assignments": [{
                "persona_id": "test"
                # Missing provider and model
            }]
        })
        assert response.status_code == 422  # Validation error
    
    def test_database_error_handling(self, client):
        """Test that database errors are handled gracefully."""
        # This test would need to simulate database failures
        # For now, just ensure endpoints are robust
        response = client.get("/api/setup/assessment")
        assert response.status_code == 200
        
        response = client.get("/api/setup/check-first-run")
        assert response.status_code == 200

class TestSecurityAndValidation:
    """Test security and input validation."""
    
    def test_sql_injection_protection(self, authenticated_client):
        """Test protection against SQL injection in persona IDs."""
        malicious_id = "'; DROP TABLE users; --"
        
        response = authenticated_client.post("/api/setup/assign-models", json={
            "assignments": [{
                "persona_id": malicious_id,
                "provider": "ollama",
                "model": "llama3.1:latest"
            }],
            "preference": "balanced"
        })
        
        # Should not crash, should handle gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_xss_protection_in_api_responses(self, client):
        """Test XSS protection in API responses."""
        malicious_script = "<script>alert('xss')</script>"
        
        response = client.post("/api/setup/test-api-key", json={
            "provider": malicious_script,
            "api_key": "test"
        })
        
        # Should return safe error message
        assert response.status_code == 200
        data = response.json()
        assert "<script>" not in json.dumps(data)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])