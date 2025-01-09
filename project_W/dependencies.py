from .database import database_adapter
from .security import jwt_token_handler

db: database_adapter
jwt_handler = jwt_token_handler()
config = {}
