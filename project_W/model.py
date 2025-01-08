from pydantic import BaseModel


# user model for the api
class User(BaseModel):
    id: int
    email: str
    is_admin: bool
    activated: bool


# user model for the database
class UserInDb(User):
    password_hash: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str
    scopes: list[str] = []
