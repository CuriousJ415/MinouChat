from sqlalchemy import Column, String, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from ..core.database import Base

class Personality(Base):
    __tablename__ = "personalities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    system_prompt = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # XML-based configuration
    xml_config = Column(Text, nullable=True)  # Raw XML configuration
    traits = Column(JSON, nullable=True)      # Parsed traits as JSON
    model_config = Column(JSON, nullable=True)  # LLM model configuration
    
    conversations = relationship("Conversation", back_populates="personality")

    def __repr__(self):
        return f"<Personality {self.name}>" 