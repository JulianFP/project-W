from .database import postgres_adapter
from .security import jwt_token_handler

db = postgres_adapter()
jwt_handler = jwt_token_handler()
