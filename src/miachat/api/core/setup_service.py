#!/usr/bin/env python3
"""
MiaChat Setup Navigator Service

Handles system detection, configuration, and setup guidance for new users.
Ensures personas have functional models and provides setup wizards.
"""

import asyncio
import logging
import os
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"

class ModelStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NEEDS_SETUP = "needs_setup"
    ERROR = "error"

@dataclass
class ModelInfo:
    """Information about a specific model"""
    provider: ModelProvider
    model_name: str
    status: ModelStatus
    size_gb: Optional[float] = None
    description: Optional[str] = None
    privacy_level: str = "unknown"  # "local", "cloud", "hybrid"
    setup_required: bool = False
    error_message: Optional[str] = None

@dataclass
class ProviderStatus:
    """Status of an LLM provider"""
    provider: ModelProvider
    available: bool
    models: List[ModelInfo]
    api_key_configured: bool = False
    connection_tested: bool = False
    error_message: Optional[str] = None
    setup_url: Optional[str] = None

@dataclass
class PersonaModelAssignment:
    """Recommended model assignment for a persona"""
    persona_name: str
    persona_id: str
    current_model: Optional[str]
    current_provider: Optional[str]
    recommended_model: Optional[str]
    recommended_provider: Optional[str]
    status: ModelStatus
    fallback_options: List[Tuple[str, str]]  # [(provider, model), ...]

@dataclass
class SetupAssessment:
    """Complete system setup assessment"""
    timestamp: datetime
    overall_status: str  # "ready", "needs_setup", "broken"
    providers: List[ProviderStatus]
    personas: List[PersonaModelAssignment]
    recommendations: List[str]
    privacy_score: int  # 1-10, higher = more private
    setup_required: bool

class SetupService:
    """Core service for system setup and configuration"""
    
    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.docker_ollama_url = "http://host.docker.internal:11434"
        
    async def perform_full_assessment(self) -> SetupAssessment:
        """Perform complete system assessment"""
        logger.info("Starting full system assessment...")
        
        # Ensure default characters exist (without models)
        from .character_initializer import character_initializer
        character_initializer.ensure_characters_exist()
        
        # Check all providers
        providers = await asyncio.gather(
            self._check_ollama(),
            self._check_openai(),
            self._check_anthropic(),
            self._check_openrouter(),
            return_exceptions=True
        )
        
        # Filter out exceptions
        valid_providers = [p for p in providers if isinstance(p, ProviderStatus)]
        
        # Get persona recommendations
        personas = await self._assess_personas(valid_providers)
        
        # Generate overall assessment
        assessment = SetupAssessment(
            timestamp=datetime.now(),
            overall_status=self._determine_overall_status(valid_providers, personas),
            providers=valid_providers,
            personas=personas,
            recommendations=self._generate_recommendations(valid_providers, personas),
            privacy_score=self._calculate_privacy_score(valid_providers),
            setup_required=any(p.status == ModelStatus.NEEDS_SETUP for p in personas)
        )
        
        logger.info(f"Assessment complete. Status: {assessment.overall_status}")
        return assessment
    
    async def _check_ollama(self) -> ProviderStatus:
        """Check Ollama availability and models"""
        models = []
        available = False
        error_msg = None
        
        # Try both local and Docker URLs
        for url in [self.ollama_url, self.docker_ollama_url]:
            try:
                # Test connection
                response = requests.get(f"{url}/api/tags", timeout=5)
                if response.status_code == 200:
                    available = True
                    data = response.json()
                    
                    # Parse available models
                    for model_data in data.get("models", []):
                        name = model_data.get("name", "")
                        size = model_data.get("size", 0) / (1024**3)  # Convert to GB
                        
                        models.append(ModelInfo(
                            provider=ModelProvider.OLLAMA,
                            model_name=name,
                            status=ModelStatus.AVAILABLE,
                            size_gb=round(size, 1),
                            description=f"Local model ({size:.1f}GB)",
                            privacy_level="local",
                            setup_required=False
                        ))
                    break
                    
            except Exception as e:
                error_msg = str(e)
                continue
        
        if not available and not models:
            # Ollama not available - needs setup
            models.append(ModelInfo(
                provider=ModelProvider.OLLAMA,
                model_name="llama3.1:latest",
                status=ModelStatus.NEEDS_SETUP,
                description="Recommended general-purpose model",
                privacy_level="local",
                setup_required=True,
                error_message="Ollama not installed or not running"
            ))
        
        return ProviderStatus(
            provider=ModelProvider.OLLAMA,
            available=available,
            models=models,
            connection_tested=available,
            error_message=error_msg if not available else None,
            setup_url="https://ollama.ai/download" if not available else None
        )
    
    async def _check_openai(self) -> ProviderStatus:
        """Check OpenAI API availability"""
        api_key = os.getenv("OPENAI_API_KEY")
        available = False
        models = []
        
        if api_key:
            try:
                # Test API connection
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get("https://api.openai.com/v1/models", 
                                      headers=headers, timeout=10)
                if response.status_code == 200:
                    available = True
                    
                    # Add recommended models
                    recommended_models = [
                        ("gpt-4o", "Latest GPT-4 model"),
                        ("gpt-4", "Powerful reasoning model"),
                        ("gpt-3.5-turbo", "Fast and cost-effective")
                    ]
                    
                    for model_name, desc in recommended_models:
                        models.append(ModelInfo(
                            provider=ModelProvider.OPENAI,
                            model_name=model_name,
                            status=ModelStatus.AVAILABLE,
                            description=desc,
                            privacy_level="cloud"
                        ))
                        
            except Exception as e:
                models.append(ModelInfo(
                    provider=ModelProvider.OPENAI,
                    model_name="gpt-4o",
                    status=ModelStatus.ERROR,
                    privacy_level="cloud",
                    error_message=str(e)
                ))
        else:
            # No API key - needs setup
            models.append(ModelInfo(
                provider=ModelProvider.OPENAI,
                model_name="gpt-4o",
                status=ModelStatus.NEEDS_SETUP,
                description="Requires API key configuration",
                privacy_level="cloud",
                setup_required=True
            ))
        
        return ProviderStatus(
            provider=ModelProvider.OPENAI,
            available=available,
            models=models,
            api_key_configured=bool(api_key),
            connection_tested=available,
            setup_url="https://platform.openai.com/api-keys"
        )
    
    async def _check_anthropic(self) -> ProviderStatus:
        """Check Anthropic API availability"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        available = False
        models = []
        
        if api_key:
            try:
                # Test API connection (Anthropic doesn't have a models endpoint)
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                # We'll assume it's available if we have a key (no easy test endpoint)
                available = True
                
                recommended_models = [
                    ("claude-3-5-sonnet-20241022", "Latest Claude 3.5 Sonnet"),
                    ("claude-3-opus-20240229", "Most capable Claude model"),
                    ("claude-3-haiku-20240307", "Fast and cost-effective")
                ]
                
                for model_name, desc in recommended_models:
                    models.append(ModelInfo(
                        provider=ModelProvider.ANTHROPIC,
                        model_name=model_name,
                        status=ModelStatus.AVAILABLE,
                        description=desc,
                        privacy_level="cloud"
                    ))
                    
            except Exception as e:
                models.append(ModelInfo(
                    provider=ModelProvider.ANTHROPIC,
                    model_name="claude-3-5-sonnet-20241022",
                    status=ModelStatus.ERROR,
                    privacy_level="cloud",
                    error_message=str(e)
                ))
        else:
            models.append(ModelInfo(
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-5-sonnet-20241022",
                status=ModelStatus.NEEDS_SETUP,
                description="Requires API key configuration",
                privacy_level="cloud",
                setup_required=True
            ))
        
        return ProviderStatus(
            provider=ModelProvider.ANTHROPIC,
            available=available,
            models=models,
            api_key_configured=bool(api_key),
            connection_tested=available,
            setup_url="https://console.anthropic.com/"
        )
    
    async def _check_openrouter(self) -> ProviderStatus:
        """Check OpenRouter API availability"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        available = False
        models = []
        
        if api_key:
            try:
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get("https://openrouter.ai/api/v1/models", 
                                      headers=headers, timeout=10)
                if response.status_code == 200:
                    available = True
                    
                    # Add some popular models
                    recommended_models = [
                        ("openai/gpt-4o", "GPT-4o via OpenRouter"),
                        ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
                        ("meta-llama/llama-3.1-8b-instruct", "Llama 3.1 8B")
                    ]
                    
                    for model_name, desc in recommended_models:
                        models.append(ModelInfo(
                            provider=ModelProvider.OPENROUTER,
                            model_name=model_name,
                            status=ModelStatus.AVAILABLE,
                            description=desc,
                            privacy_level="cloud"
                        ))
                        
            except Exception as e:
                models.append(ModelInfo(
                    provider=ModelProvider.OPENROUTER,
                    model_name="openai/gpt-4o",
                    status=ModelStatus.ERROR,
                    privacy_level="cloud",
                    error_message=str(e)
                ))
        else:
            models.append(ModelInfo(
                provider=ModelProvider.OPENROUTER,
                model_name="openai/gpt-4o",
                status=ModelStatus.NEEDS_SETUP,
                description="Requires API key configuration",
                privacy_level="cloud",
                setup_required=True
            ))
        
        return ProviderStatus(
            provider=ModelProvider.OPENROUTER,
            available=available,
            models=models,
            api_key_configured=bool(api_key),
            connection_tested=available,
            setup_url="https://openrouter.ai/keys"
        )
    
    async def _assess_personas(self, providers: List[ProviderStatus]) -> List[PersonaModelAssignment]:
        """Assess persona model assignments and make recommendations"""
        from .character_manager import character_manager
        
        personas = []
        characters = character_manager.list_characters()
        
        # Get available models from all providers
        available_models = []
        for provider in providers:
            if provider.available:
                for model in provider.models:
                    if model.status == ModelStatus.AVAILABLE:
                        available_models.append((provider.provider.value, model.model_name))
        
        for character in characters:
            current_config = character.get('model_config') or {}
            current_provider = current_config.get('provider')
            current_model = current_config.get('model')
            
            # Check if current config is working
            current_works = (current_provider, current_model) in available_models
            
            # Find best recommendation
            recommended_provider, recommended_model = self._get_best_model_recommendation(
                available_models, character.get('category', 'General')
            )
            
            # Generate fallback options
            fallback_options = available_models[:3]  # Top 3 available
            
            personas.append(PersonaModelAssignment(
                persona_name=character['name'],
                persona_id=character['id'],
                current_model=current_model,
                current_provider=current_provider,
                recommended_model=recommended_model,
                recommended_provider=recommended_provider,
                status=ModelStatus.AVAILABLE if current_works else ModelStatus.NEEDS_SETUP,
                fallback_options=fallback_options
            ))
        
        return personas
    
    def _get_best_model_recommendation(self, available_models: List[Tuple[str, str]], 
                                     category: str) -> Tuple[Optional[str], Optional[str]]:
        """Get best model recommendation based on category and availability"""
        
        # Priority order: local models first (privacy), then cloud
        preference_order = [
            # Local models (Ollama) - highest privacy
            ("ollama", "llama3.1:latest"),
            ("ollama", "llama3:latest"),
            ("ollama", "mistral:latest"),
            
            # Cloud models - for when local isn't available
            ("openai", "gpt-4o"),
            ("anthropic", "claude-3-5-sonnet-20241022"),
            ("openrouter", "openai/gpt-4o"),
        ]
        
        for provider, model in preference_order:
            if (provider, model) in available_models:
                return provider, model
        
        # If nothing from preference list, return first available
        if available_models:
            return available_models[0]
        
        return None, None
    
    def _determine_overall_status(self, providers: List[ProviderStatus], 
                                personas: List[PersonaModelAssignment]) -> str:
        """Determine overall system status"""
        
        # Check if any provider is working
        any_provider_working = any(p.available for p in providers)
        
        # Check if all personas have working models
        all_personas_working = all(p.status == ModelStatus.AVAILABLE for p in personas)
        
        if any_provider_working and all_personas_working:
            return "ready"
        elif any_provider_working:
            return "needs_setup"
        else:
            return "broken"
    
    def _generate_recommendations(self, providers: List[ProviderStatus], 
                                personas: List[PersonaModelAssignment]) -> List[str]:
        """Generate setup recommendations"""
        recommendations = []
        
        # Check for Ollama
        ollama_provider = next((p for p in providers if p.provider == ModelProvider.OLLAMA), None)
        if not ollama_provider or not ollama_provider.available:
            recommendations.append(
                "🔒 Install Ollama for complete privacy and local AI processing"
            )
        
        # Check for broken personas
        broken_personas = [p for p in personas if p.status != ModelStatus.AVAILABLE]
        if broken_personas:
            recommendations.append(
                f"⚠️ {len(broken_personas)} personas need model configuration"
            )
        
        # Privacy recommendation
        local_available = any(p.provider == ModelProvider.OLLAMA and p.available for p in providers)
        if not local_available:
            recommendations.append(
                "🌐 Consider cloud providers (OpenAI, Anthropic) for immediate access"
            )
        
        return recommendations
    
    def _calculate_privacy_score(self, providers: List[ProviderStatus]) -> int:
        """Calculate privacy score (1-10, higher = more private)"""
        
        # Start with base score
        score = 5
        
        # Local models boost privacy significantly
        ollama_provider = next((p for p in providers if p.provider == ModelProvider.OLLAMA), None)
        if ollama_provider and ollama_provider.available:
            local_models = len([m for m in ollama_provider.models if m.status == ModelStatus.AVAILABLE])
            score += min(local_models * 2, 5)  # Up to +5 for local models
        
        # Cloud providers reduce privacy
        cloud_providers = [p for p in providers if p.provider != ModelProvider.OLLAMA and p.available]
        if cloud_providers and not (ollama_provider and ollama_provider.available):
            score -= 2  # -2 if only cloud available
        
        return max(1, min(10, score))

# Global instance
setup_service = SetupService()