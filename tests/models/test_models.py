import pytest
from miachat.database.models import Conversation, Message, Base
from miachat.database.config import DatabaseConfig
from sqlalchemy.orm import sessionmaker
import tempfile
import os

@pytest.fixture(scope="module")
def db_session():
    # Use a temporary SQLite database for testing
    db_fd, db_path = tempfile.mkstemp()
    db_url = f"sqlite:///{db_path}"
    db_config = DatabaseConfig(db_url)
    Base.metadata.create_all(bind=db_config.engine)
    Session = sessionmaker(bind=db_config.engine)
    session = Session()
    yield session
    session.close()
    os.close(db_fd)
    os.unlink(db_path)

def test_create_conversation_and_message(db_session):
    conversation = Conversation.create(personality_id=1, metadata={"test": True})
    db_session.add(conversation)
    db_session.commit()
    assert conversation.id is not None

    message = Message.create(
        conversation_id=conversation.id,
        content="Hello, world!",
        role="user",
        metadata={"test": True}
    )
    db_session.add(message)
    db_session.commit()
    assert message.id is not None

    # Query back
    conv = db_session.query(Conversation).filter_by(id=conversation.id).first()
    assert conv is not None
    msg = db_session.query(Message).filter_by(id=message.id).first()
    assert msg is not None
    assert msg.content == "Hello, world!" 