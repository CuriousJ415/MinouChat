"""
NPC (Non-Player Character) System
Handles limited-role characters that exist in the character's world.
"""
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

@dataclass
class NPCMoment:
    """Represents a significant moment involving an NPC"""
    description: str
    timestamp: datetime
    impact: float  # -1.0 to 1.0, negative being negative impact
    category: str  # e.g., "conflict", "bonding", "learning"

class NPC:
    """Represents a non-player character with limited role"""
    
    def __init__(self, name: str, role: str, relationship: str):
        self.name = name
        self.role = role  # e.g., "friend", "mentor", "rival"
        self.relationship = relationship
        self.key_moments: List[NPCMoment] = []
        self.trust_level: float = 0.5  # 0.0 to 1.0
        self.influence: float = 0.5  # 0.0 to 1.0, how much they influence the main character
    
    def add_moment(self, description: str, impact: float, category: str) -> None:
        """Add a significant moment to the NPC's history"""
        moment = NPCMoment(
            description=description,
            timestamp=datetime.now(),
            impact=impact,
            category=category
        )
        self.key_moments.append(moment)
        
        # Update trust level based on moment impact
        self.trust_level = max(0.0, min(1.0, self.trust_level + (impact * 0.1)))
    
    def get_recent_moments(self, count: int = 5) -> List[NPCMoment]:
        """Get the most recent significant moments"""
        return sorted(
            self.key_moments,
            key=lambda x: x.timestamp,
            reverse=True
        )[:count]
    
    def get_moments_by_category(self, category: str) -> List[NPCMoment]:
        """Get all moments of a specific category"""
        return [m for m in self.key_moments if m.category == category]
    
    def save_state(self, filepath: str) -> None:
        """Save NPC state to a file"""
        state = {
            'name': self.name,
            'role': self.role,
            'relationship': self.relationship,
            'trust_level': self.trust_level,
            'influence': self.influence,
            'key_moments': [
                {
                    'description': m.description,
                    'timestamp': m.timestamp.isoformat(),
                    'impact': m.impact,
                    'category': m.category
                }
                for m in self.key_moments
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
    
    @classmethod
    def load_state(cls, filepath: str) -> 'NPC':
        """Load NPC state from a file"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        npc = cls(
            name=state['name'],
            role=state['role'],
            relationship=state['relationship']
        )
        
        npc.trust_level = state['trust_level']
        npc.influence = state['influence']
        npc.key_moments = [
            NPCMoment(
                description=m['description'],
                timestamp=datetime.fromisoformat(m['timestamp']),
                impact=m['impact'],
                category=m['category']
            )
            for m in state['key_moments']
        ]
        
        return npc

class NPCManager:
    """Manages all NPCs in the character's world"""
    
    def __init__(self):
        self.npcs: Dict[str, NPC] = {}
    
    def add_npc(self, npc: NPC) -> None:
        """Add an NPC to the manager"""
        self.npcs[npc.name] = npc
    
    def get_npc(self, name: str) -> Optional[NPC]:
        """Get an NPC by name"""
        return self.npcs.get(name)
    
    def remove_npc(self, name: str) -> None:
        """Remove an NPC from the manager"""
        if name in self.npcs:
            del self.npcs[name]
    
    def get_npcs_by_role(self, role: str) -> List[NPC]:
        """Get all NPCs with a specific role"""
        return [npc for npc in self.npcs.values() if npc.role == role]
    
    def save_all_states(self, directory: str) -> None:
        """Save all NPC states to files"""
        for npc in self.npcs.values():
            filepath = f"{directory}/{npc.name.lower().replace(' ', '_')}.json"
            npc.save_state(filepath)
    
    @classmethod
    def load_all_states(cls, directory: str) -> 'NPCManager':
        """Load all NPC states from files"""
        manager = cls()
        # TODO: Implement directory scanning and loading
        return manager 