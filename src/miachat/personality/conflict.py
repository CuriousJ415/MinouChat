"""
User-Character Conflict Resolution System
Handles conflicts and disagreements between the user and the character.
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from .schema import PersonalityDefinition

@dataclass
class Conflict:
    """Represents a conflict between user and character"""
    description: str
    timestamp: datetime
    severity: float  # 0.0 to 1.0
    category: str  # e.g., "disagreement", "misunderstanding", "betrayal"
    resolution: Optional[str] = None
    impact: Optional[float] = None  # -1.0 to 1.0, negative being negative impact

class ConflictResolver:
    """Handles conflict resolution between user and character"""
    
    def __init__(self, personality: PersonalityDefinition):
        self.personality = personality
        self.conflict_history: List[Conflict] = []
        self.trust_level: float = 0.5  # 0.0 to 1.0
        self.resolution_strategies: Dict[str, callable] = {
            'disagreement': self._resolve_disagreement,
            'misunderstanding': self._resolve_misunderstanding,
            'betrayal': self._resolve_betrayal
        }
    
    def handle_conflict(self, description: str, category: str, severity: float) -> Tuple[str, float]:
        """
        Handle a new conflict and return the character's response and trust impact
        Returns: (response, trust_impact)
        """
        # Create new conflict record
        conflict = Conflict(
            description=description,
            timestamp=datetime.now(),
            severity=severity,
            category=category
        )
        
        # Get resolution strategy based on category
        if category in self.resolution_strategies:
            response, impact = self.resolution_strategies[category](conflict)
        else:
            response, impact = self._resolve_generic(conflict)
        
        # Update conflict record
        conflict.resolution = response
        conflict.impact = impact
        
        # Update trust level
        self.trust_level = max(0.0, min(1.0, self.trust_level + impact))
        
        # Add to history
        self.conflict_history.append(conflict)
        
        return response, impact
    
    def _resolve_disagreement(self, conflict: Conflict) -> Tuple[str, float]:
        """Resolve a disagreement based on personality traits"""
        empathy = next(t.value for t in self.personality.traits if t.name == 'empathy')
        adaptability = next(t.value for t in self.personality.traits if t.name == 'adaptability')
        
        if empathy > 0.7:
            response = "I understand your perspective, and while I may not fully agree, I respect your viewpoint."
            impact = 0.05
        elif adaptability > 0.7:
            response = "I see your point. Let's find a middle ground that works for both of us."
            impact = 0.03
        else:
            response = "I have a different view on this, but I'm willing to discuss it further."
            impact = 0.01
            
        return response, impact
    
    def _resolve_misunderstanding(self, conflict: Conflict) -> Tuple[str, float]:
        """Resolve a misunderstanding based on personality traits"""
        empathy = next(t.value for t in self.personality.traits if t.name == 'empathy')
        intelligence = next(t.value for t in self.personality.traits if t.name == 'intelligence')
        
        if empathy > 0.7 and intelligence > 0.7:
            response = "I think there might have been a misunderstanding. Let me clarify my position..."
            impact = 0.02
        else:
            response = "I apologize for any confusion. Let me explain what I meant."
            impact = 0.01
            
        return response, impact
    
    def _resolve_betrayal(self, conflict: Conflict) -> Tuple[str, float]:
        """Resolve a betrayal based on personality traits"""
        empathy = next(t.value for t in self.personality.traits if t.name == 'empathy')
        reliability = next(t.value for t in self.personality.traits if t.name == 'reliability')
        
        if empathy > 0.8 and reliability > 0.8:
            response = "This has hurt our trust, but I believe we can work through this together."
            impact = -0.1
        else:
            response = "This is a serious breach of trust. We need to address this directly."
            impact = -0.2
            
        return response, impact
    
    def _resolve_generic(self, conflict: Conflict) -> Tuple[str, float]:
        """Generic conflict resolution"""
        response = "I understand this is a difficult situation. Let's work together to resolve it."
        impact = 0.0
        return response, impact
    
    def get_recent_conflicts(self, count: int = 5) -> List[Conflict]:
        """Get the most recent conflicts"""
        return sorted(
            self.conflict_history,
            key=lambda x: x.timestamp,
            reverse=True
        )[:count]
    
    def get_conflicts_by_category(self, category: str) -> List[Conflict]:
        """Get all conflicts of a specific category"""
        return [c for c in self.conflict_history if c.category == category]
    
    def save_state(self, filepath: str) -> None:
        """Save conflict resolution state to a file"""
        state = {
            'trust_level': self.trust_level,
            'conflict_history': [
                {
                    'description': c.description,
                    'timestamp': c.timestamp.isoformat(),
                    'severity': c.severity,
                    'category': c.category,
                    'resolution': c.resolution,
                    'impact': c.impact
                }
                for c in self.conflict_history
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    @classmethod
    def load_state(cls, personality: PersonalityDefinition, filepath: str) -> 'ConflictResolver':
        """Load conflict resolution state from a file"""
        resolver = cls(personality)
        
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
                
            resolver.trust_level = state['trust_level']
            resolver.conflict_history = [
                Conflict(
                    description=c['description'],
                    timestamp=datetime.fromisoformat(c['timestamp']),
                    severity=c['severity'],
                    category=c['category'],
                    resolution=c['resolution'],
                    impact=c['impact']
                )
                for c in state['conflict_history']
            ]
        except FileNotFoundError:
            pass  # Start with default state if file doesn't exist
            
        return resolver 