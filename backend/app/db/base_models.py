"""
Import all SQLAlchemy models here to ensure they are registered with Base.metadata.
This file should be imported whenever you need to create all tables.
"""
from app.db.base_class import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.context import Context  # noqa: F401
from app.models.health import Health  # noqa: F401 