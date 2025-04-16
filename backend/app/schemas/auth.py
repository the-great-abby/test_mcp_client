from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """
    Schema for login request.
    """
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """
    Schema for login response.
    """
    access_token: str
    token_type: str = "bearer" 