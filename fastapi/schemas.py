from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str

class UserInDB(UserCreate):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class TodoCreate(BaseModel):
    title: str
    description: str

class TodoInDB(TodoCreate):
    owner_id: int

class TodoGet(BaseModel):
    id: int
    title: str
    description: str