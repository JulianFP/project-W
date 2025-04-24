from pydantic import BaseModel


class UserInDb(BaseModel):
    id: int
    email: str
