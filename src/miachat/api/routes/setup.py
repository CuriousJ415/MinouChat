#!/usr/bin/env python3
"""
Setup Navigator API Routes

Provides endpoints for the MiaChat setup wizard and system assessment.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from ..core.setup_service import setup_service, SetupAssessment, PersonaModelAssignment
from ..core.clerk_auth import get_current_user_from_session
from ...database.config import get_db
from ..core.character_manager import character_manager
from ..core.character_initializer import character_initializer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/setup", tags=["setup"])

# Pydantic models for API responses
class ModelInfoResponse(BaseModel):
    provider: str
    model_name: str
    status: str
    size_gb: Optional[float] = None
    description: Optional[str] = None
    privacy_level: str
    setup_required: bool = False
    error_message: Optional[str] = None

class ProviderStatusResponse(BaseModel):
    provider: str
    available: bool
    models: List[ModelInfoResponse]
    api_key_configured: bool = False
    connection_tested: bool = False
    error_message: Optional[str] = None
    setup_url: Optional[str] = None

class PersonaAssignmentResponse(BaseModel):
    persona_name: str
    persona_id: str
    current_model: Optional[str]
    current_provider: Optional[str]
    recommended_model: Optional[str]
    recommended_provider: Optional[str]
    status: str
    fallback_options: List[List[str]]  # List of [provider, model] pairs

class SetupAssessmentResponse(BaseModel):
    timestamp: str
    overall_status: str
    providers: List[ProviderStatusResponse]
    personas: List[PersonaAssignmentResponse]
    recommendations: List[str]
    privacy_score: int
    setup_required: bool

class ModelAssignmentRequest(BaseModel):
    persona_id: str
    provider: str
    model: str

class BulkAssignmentRequest(BaseModel):
    assignments: List[ModelAssignmentRequest]
    preference: str = "privacy"  # "privacy", "performance", "cost"

@router.get("/assessment", response_model=SetupAssessmentResponse)
async def get_system_assessment(request: Request, db = Depends(get_db)):
    """Get complete system assessment for setup wizard"""
    
    # Note: This endpoint can be accessed without authentication for initial setup
    # current_user = await get_current_user_from_session(request, db)
    
    try:
        assessment = await setup_service.perform_full_assessment()
        
        # Convert to response format
        return SetupAssessmentResponse(
            timestamp=assessment.timestamp.isoformat(),
            overall_status=assessment.overall_status,
            providers=[
                ProviderStatusResponse(
                    provider=p.provider.value,
                    available=p.available,
                    models=[
                        ModelInfoResponse(
                            provider=m.provider.value,
                            model_name=m.model_name,
                            status=m.status.value,
                            size_gb=m.size_gb,
                            description=m.description,
                            privacy_level=m.privacy_level,
                            setup_required=m.setup_required,
                            error_message=m.error_message
                        ) for m in p.models
                    ],
                    api_key_configured=p.api_key_configured,
                    connection_tested=p.connection_tested,
                    error_message=p.error_message,
                    setup_url=p.setup_url
                ) for p in assessment.providers
            ],
            personas=[
                PersonaAssignmentResponse(
                    persona_name=pa.persona_name,
                    persona_id=pa.persona_id,
                    current_model=pa.current_model,
                    current_provider=pa.current_provider,
                    recommended_model=pa.recommended_model,
                    recommended_provider=pa.recommended_provider,
                    status=pa.status.value,
                    fallback_options=[[provider, model] for provider, model in pa.fallback_options]
                ) for pa in assessment.personas
            ],
            recommendations=assessment.recommendations,
            privacy_score=assessment.privacy_score,
            setup_required=assessment.setup_required
        )
        
    except Exception as e:
        logger.error(f"Error performing system assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")

@router.post("/assign-models")
async def assign_models_to_personas(
    request: BulkAssignmentRequest,
    request_obj: Request,
    db = Depends(get_db)
):
    """Assign models to personas based on user preferences"""
    
    current_user = await get_current_user_from_session(request_obj, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        updated_personas = []
        
        for assignment in request.assignments:
            # Update character configuration
            update_data = {
                "model_config": {
                    "provider": assignment.provider,
                    "model": assignment.model,
                    "temperature": 0.7  # Default temperature
                }
            }
            
            character = character_manager.update_character(assignment.persona_id, update_data)
            if character:
                updated_personas.append({
                    "persona_id": assignment.persona_id,
                    "persona_name": character["name"],
                    "provider": assignment.provider,
                    "model": assignment.model,
                    "status": "updated"
                })
                logger.info(f"Updated {character['name']} to use {assignment.provider}:{assignment.model}")
            else:
                updated_personas.append({
                    "persona_id": assignment.persona_id,
                    "status": "error",
                    "error": "Character not found"
                })
        
        return {
            "success": True,
            "updated_personas": updated_personas,
            "message": f"Updated {len(updated_personas)} personas"
        }
        
    except Exception as e:
        logger.error(f"Error assigning models: {e}")
        raise HTTPException(status_code=500, detail=f"Model assignment failed: {str(e)}")

@router.post("/auto-configure")
async def auto_configure_system(
    preference: str = "privacy",  # "privacy", "performance", "cost"
    request: Request = None,
    db = Depends(get_db)
):
    """Automatically configure the system based on user preference"""
    
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Get system assessment
        assessment = await setup_service.perform_full_assessment()
        
        # Generate automatic assignments based on preference
        assignments = []
        
        for persona in assessment.personas:
            if persona.recommended_provider and persona.recommended_model:
                assignments.append(ModelAssignmentRequest(
                    persona_id=persona.persona_id,
                    provider=persona.recommended_provider,
                    model=persona.recommended_model
                ))
        
        # Apply assignments
        if assignments:
            bulk_request = BulkAssignmentRequest(
                assignments=assignments,
                preference=preference
            )
            result = await assign_models_to_personas(bulk_request, request, db)
            
            return {
                "success": True,
                "message": f"Auto-configured {len(assignments)} personas for {preference}",
                "preference": preference,
                "assignments": result["updated_personas"]
            }
        else:
            return {
                "success": False,
                "message": "No working models found for auto-configuration",
                "assignments": []
            }
            
    except Exception as e:
        logger.error(f"Error in auto-configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Auto-configuration failed: {str(e)}")

@router.get("/providers/{provider}/test")
async def test_provider_connection(provider: str):
    """Test connection to a specific provider"""
    
    try:
        assessment = await setup_service.perform_full_assessment()
        provider_status = next((p for p in assessment.providers if p.provider.value == provider), None)
        
        if not provider_status:
            raise HTTPException(status_code=404, detail=f"Provider {provider} not found")
        
        return {
            "provider": provider,
            "available": provider_status.available,
            "connection_tested": provider_status.connection_tested,
            "models_found": len(provider_status.models),
            "error_message": provider_status.error_message,
            "setup_url": provider_status.setup_url
        }
        
    except Exception as e:
        logger.error(f"Error testing provider {provider}: {e}")
        raise HTTPException(status_code=500, detail=f"Provider test failed: {str(e)}")

@router.get("/check-first-run")
async def check_first_run():
    """Check if this is a first-run that needs setup"""
    
    try:
        # Check if characters need initialization/setup
        needs_char_init = character_initializer.check_needs_initialization()
        unconfigured_chars = character_initializer.get_unonfigured_characters()
        
        assessment = await setup_service.perform_full_assessment()
        
        # Determine if setup is needed
        needs_setup = (
            needs_char_init or
            len(unconfigured_chars) > 0 or
            assessment.overall_status in ["broken", "needs_setup"] or
            assessment.setup_required or
            not any(p.available for p in assessment.providers)
        )
        
        return {
            "first_run": needs_setup,
            "overall_status": assessment.overall_status,
            "setup_required": assessment.setup_required,
            "characters_need_init": needs_char_init,
            "unconfigured_characters": len(unconfigured_chars),
            "providers_available": len([p for p in assessment.providers if p.available]),
            "personas_working": len([p for p in assessment.personas if p.status.value == "available"]),
            "recommendations": assessment.recommendations[:3]  # Top 3 recommendations
        }
        
    except Exception as e:
        logger.error(f"Error checking first run: {e}")
        return {
            "first_run": True,
            "error": str(e)
        }

@router.post("/initialize-characters")
async def initialize_default_characters(request: Request, db = Depends(get_db)):
    """Initialize default characters without model assignments"""
    
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Initialize default characters
        created_characters = character_initializer.initialize_default_characters()
        
        return {
            "success": True,
            "message": f"Initialized {len(created_characters)} default characters",
            "characters": [
                {
                    "id": char["id"],
                    "name": char["name"],
                    "category": char["category"],
                    "setup_required": char.get("setup_required", True)
                }
                for char in created_characters
            ]
        }
        
    except Exception as e:
        logger.error(f"Error initializing characters: {e}")
        raise HTTPException(status_code=500, detail=f"Character initialization failed: {str(e)}")

@router.post("/reset-models")
async def reset_character_models(request: Request, db = Depends(get_db)):
    """Reset all character model assignments (for testing)"""
    
    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        reset_count = character_initializer.reset_character_models()
        
        return {
            "success": True,
            "message": f"Reset {reset_count} character model configurations",
            "reset_count": reset_count
        }
        
    except Exception as e:
        logger.error(f"Error resetting models: {e}")
        raise HTTPException(status_code=500, detail=f"Model reset failed: {str(e)}")

# ==================== RESET API ENDPOINTS ====================

# Use a separate router for reset endpoints under /api/reset
reset_router = APIRouter(prefix="/api/reset", tags=["reset"])

@reset_router.delete("/full")
async def reset_full(request: Request, db = Depends(get_db)):
    """Full factory reset - clears everything and restores defaults"""

    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        from ...database.models import Conversation, Message, Document, ConversationFact

        # Clear all conversations and messages
        db.query(Message).delete()
        db.query(Conversation).delete()

        # Clear all documents
        db.query(Document).delete()

        # Clear all learned facts
        db.query(ConversationFact).delete()

        db.commit()

        # Delete all character cards (user-created ones)
        import os
        import glob
        character_cards_dir = os.path.join(os.getcwd(), "character_cards")
        if os.path.exists(character_cards_dir):
            for file in glob.glob(os.path.join(character_cards_dir, "*.json")):
                try:
                    os.remove(file)
                except:
                    pass

        # Re-initialize default characters
        created_characters = character_initializer.initialize_default_characters()

        logger.info(f"Full reset completed. Restored {len(created_characters)} default characters.")

        return {
            "success": True,
            "message": "Application reset to defaults",
            "restored_characters": len(created_characters)
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error during full reset: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@reset_router.delete("/user-data")
async def reset_user_data(request: Request, db = Depends(get_db)):
    """Clear user data (conversations, facts, documents) but keep characters"""

    current_user = await get_current_user_from_session(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        from ...database.models import Conversation, Message, Document, ConversationFact

        # Clear all conversations and messages
        db.query(Message).delete()
        db.query(Conversation).delete()

        # Clear all documents
        db.query(Document).delete()

        # Clear all learned facts
        db.query(ConversationFact).delete()

        db.commit()

        logger.info("User data reset completed. Characters preserved.")

        return {
            "success": True,
            "message": "User data cleared successfully"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error during user data reset: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


class ApiKeyTestRequest(BaseModel):
    provider: str
    api_key: str

@router.post("/test-api-key")
async def test_api_key(request: ApiKeyTestRequest):
    """Test if an API key is valid for a provider"""
    
    try:
        import os
        import requests
        
        provider = request.provider.lower()
        api_key = request.api_key.strip()
        
        if not api_key:
            return {"success": False, "message": "API key is required"}
        
        # Test the API key based on provider
        if provider == "openai":
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://api.openai.com/v1/models", 
                                  headers=headers, timeout=10)
            if response.status_code == 200:
                # Store API key in environment for this session
                os.environ["OPENAI_API_KEY"] = api_key
                return {"success": True, "message": "OpenAI API key is valid"}
            else:
                return {"success": False, "message": "Invalid OpenAI API key"}
                
        elif provider == "anthropic":
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            # Anthropic doesn't have a models endpoint, so we test with a minimal completion
            test_data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            response = requests.post("https://api.anthropic.com/v1/messages",
                                   headers=headers, json=test_data, timeout=10)
            if response.status_code in [200, 400]:  # 400 might be rate limit but key is valid
                os.environ["ANTHROPIC_API_KEY"] = api_key
                return {"success": True, "message": "Anthropic API key is valid"}
            else:
                return {"success": False, "message": "Invalid Anthropic API key"}
                
        elif provider == "openrouter":
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://openrouter.ai/api/v1/models",
                                  headers=headers, timeout=10)
            if response.status_code == 200:
                os.environ["OPENROUTER_API_KEY"] = api_key
                return {"success": True, "message": "OpenRouter API key is valid"}
            else:
                return {"success": False, "message": "Invalid OpenRouter API key"}
        else:
            return {"success": False, "message": f"Unknown provider: {provider}"}
            
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Connection timeout - please try again"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}
    except Exception as e:
        logger.error(f"Error testing API key for {request.provider}: {e}")
        return {"success": False, "message": f"API key test failed: {str(e)}"}