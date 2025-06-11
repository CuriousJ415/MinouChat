"""
Initialize database with predefined personalities.
"""

from sqlalchemy.orm import Session
from .models import (
    Personality, Trait, KnowledgeDomain, Skill, Interest,
    Backstory, personality_trait, personality_knowledge_domain,
    personality_skill, personality_interest
)
from ..personality.reference import PersonalityMapper

def init_personalities(db: Session):
    """Initialize database with predefined personalities."""
    # Create personality mapper
    mapper = PersonalityMapper()
    
    # Get all references
    references = {
        name: mapper.get_reference(name)
        for name in mapper.list_references()
    }
    
    # Create traits
    traits = {}
    for ref in references.values():
        for trait_name, value in ref.traits.items():
            if trait_name not in traits:
                trait = Trait(
                    name=trait_name,
                    value=value,
                    description=f"Trait: {trait_name}"
                )
                db.add(trait)
                traits[trait_name] = trait
    
    # Create knowledge domains
    domains = {}
    for ref in references.values():
        for domain_name in ref.knowledge["domains"]:
            if domain_name not in domains:
                domain = KnowledgeDomain(
                    name=domain_name,
                    description=f"Knowledge domain: {domain_name}"
                )
                db.add(domain)
                domains[domain_name] = domain
    
    # Create skills
    skills = {}
    for ref in references.values():
        for skill_name in ref.knowledge["skills"]:
            if skill_name not in skills:
                skill = Skill(
                    name=skill_name,
                    description=f"Skill: {skill_name}"
                )
                db.add(skill)
                skills[skill_name] = skill
    
    # Create interests
    interests = {}
    for ref in references.values():
        for interest_name in ref.knowledge["interests"]:
            if interest_name not in interests:
                interest = Interest(
                    name=interest_name,
                    description=f"Interest: {interest_name}"
                )
                db.add(interest)
                interests[interest_name] = interest
    
    # Create personalities
    for ref_name, ref in references.items():
        # Create personality
        personality = Personality(
            name=ref.name,
            version="1.0",
            tone=ref.style["tone"],
            vocabulary_level=ref.style["vocabulary_level"],
            formality=float(ref.style["formality"]),
            humor_level=float(ref.style["humor_level"])
        )
        db.add(personality)
        
        # Add traits
        for trait_name, value in ref.traits.items():
            personality.traits.append(traits[trait_name])
        
        # Add knowledge domains
        for domain_name in ref.knowledge["domains"]:
            personality.knowledge_domains.append(domains[domain_name])
        
        # Add skills
        for skill_name in ref.knowledge["skills"]:
            personality.skills.append(skills[skill_name])
        
        # Add interests
        for interest_name in ref.knowledge["interests"]:
            personality.interests.append(interests[interest_name])
        
        # Create backstory
        backstory = Backstory(
            personality=personality,
            background=ref.backstory["background"],
            experiences=ref.backstory["experiences"],
            relationships=ref.backstory["relationships"],
            goals=ref.backstory["goals"]
        )
        db.add(backstory)
    
    # Commit all changes
    db.commit()

def init_db(db: Session):
    """Initialize the database with all required data."""
    init_personalities(db) 