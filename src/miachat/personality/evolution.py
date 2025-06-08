"""
Character Evolution System
Handles personality evolution based on user interactions and relationship dynamics.
"""
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

from .schema import PersonalityDefinition, PersonalityTrait

@dataclass
class Interaction:
    """Represents a single interaction between user and character"""
    user_message: str
    character_response: str
    timestamp: datetime
    emotional_tone: Optional[float] = None  # -1.0 to 1.0, negative being negative emotions
    trust_impact: Optional[float] = None    # -1.0 to 1.0, negative being trust decrease

class CharacterEvolution:
    """Manages character personality evolution based on interactions"""
    
    def __init__(self, personality: PersonalityDefinition):
        self.personality = personality
        self.interaction_history: List[Interaction] = []
        self.trust_level: float = 0.5  # 0.0 to 1.0
        self.evolution_rules: Dict[str, callable] = {
            'empathy': self._evolve_empathy,
            'adaptability': self._evolve_adaptability,
            'reliability': self._evolve_reliability,
            'creativity': self._evolve_creativity,
            'intelligence': self._evolve_intelligence
        }
    
    def process_interaction(self, user_message: str, character_response: str) -> None:
        """Process a new interaction and update personality traits"""
        # Create new interaction record
        interaction = Interaction(
            user_message=user_message,
            character_response=character_response,
            timestamp=datetime.now()
        )
        
        # Analyze emotional tone of interaction
        interaction.emotional_tone = self._analyze_emotional_tone(user_message, character_response)
        
        # Calculate trust impact
        interaction.trust_impact = self._calculate_trust_impact(interaction)
        
        # Update trust level
        self.trust_level = max(0.0, min(1.0, self.trust_level + interaction.trust_impact))
        
        # Apply evolution rules to traits
        for trait in self.personality.traits:
            if trait.name in self.evolution_rules:
                new_value = self.evolution_rules[trait.name](trait, interaction)
                trait.value = max(0.0, min(1.0, new_value))
        
        # Add to history
        self.interaction_history.append(interaction)
    
    def _analyze_emotional_tone(self, user_message: str, character_response: str) -> float:
        """Analyze the emotional tone of an interaction"""
        # TODO: Implement more sophisticated emotional analysis
        # For now, return a neutral tone
        return 0.0
    
    def _calculate_trust_impact(self, interaction: Interaction) -> float:
        """Calculate how the interaction affects trust level"""
        # TODO: Implement more sophisticated trust calculation
        # For now, return a small positive impact
        return 0.01
    
    def _evolve_empathy(self, trait: PersonalityTrait, interaction: Interaction) -> float:
        """Evolve empathy trait based on interaction"""
        if interaction.emotional_tone is None:
            return trait.value
            
        # Empathy increases when user shows emotional content
        if abs(interaction.emotional_tone) > 0.5:
            return trait.value + (0.02 * interaction.emotional_tone)
        return trait.value
    
    def _evolve_adaptability(self, trait: PersonalityTrait, interaction: Interaction) -> float:
        """Evolve adaptability trait based on interaction"""
        # Adaptability increases with successful conflict resolution
        if interaction.trust_impact and interaction.trust_impact > 0:
            return trait.value + (0.01 * interaction.trust_impact)
        return trait.value
    
    def _evolve_reliability(self, trait: PersonalityTrait, interaction: Interaction) -> float:
        """Evolve reliability trait based on interaction"""
        # Reliability increases with consistent positive interactions
        if interaction.trust_impact and interaction.trust_impact > 0:
            return trait.value + (0.01 * interaction.trust_impact)
        return trait.value
    
    def _evolve_creativity(self, trait: PersonalityTrait, interaction: Interaction) -> float:
        """Evolve creativity trait based on interaction"""
        # Creativity increases with novel or unexpected interactions
        # TODO: Implement more sophisticated creativity analysis
        return trait.value
    
    def _evolve_intelligence(self, trait: PersonalityTrait, interaction: Interaction) -> float:
        """Evolve intelligence trait based on interaction"""
        # Intelligence increases with complex or challenging interactions
        # TODO: Implement more sophisticated intelligence analysis
        return trait.value
    
    def save_evolution_state(self, filepath: str) -> None:
        """Save the current evolution state to a file"""
        state = {
            'trust_level': self.trust_level,
            'interaction_history': [
                {
                    'user_message': i.user_message,
                    'character_response': i.character_response,
                    'timestamp': i.timestamp.isoformat(),
                    'emotional_tone': i.emotional_tone,
                    'trust_impact': i.trust_impact
                }
                for i in self.interaction_history
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    @classmethod
    def load_evolution_state(cls, personality: PersonalityDefinition, filepath: str) -> 'CharacterEvolution':
        """Load evolution state from a file"""
        evolution = cls(personality)
        
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
                
            evolution.trust_level = state['trust_level']
            evolution.interaction_history = [
                Interaction(
                    user_message=i['user_message'],
                    character_response=i['character_response'],
                    timestamp=datetime.fromisoformat(i['timestamp']),
                    emotional_tone=i['emotional_tone'],
                    trust_impact=i['trust_impact']
                )
                for i in state['interaction_history']
            ]
        except FileNotFoundError:
            pass  # Start with default state if file doesn't exist
            
        return evolution 