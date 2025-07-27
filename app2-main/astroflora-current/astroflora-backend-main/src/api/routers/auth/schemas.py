from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True

# Esquemas
class Token(BaseModel):
    access_token: str
    token_type: str
