from pydantic import BaseModel, Field
from typing import Optional


class UserRegister(BaseModel):
    username: str
    publicKeyY: str
    salt: str


class UserRegisterResponse(BaseModel):
    username: str
    message: str


class ChallengeRequest(BaseModel):
    username: str
    clientR: str  # Hex string


class ChallengeResponse(BaseModel):
    challengeId: str
    c: str  
    p: str  
    q: str  
    g: str  


class VerifyRequest(BaseModel):
    challengeId: str
    s: str  
    clientR: str  
    username: str


class VerifyResponse(BaseModel):
    token: str
    type: str = "Bearer"
    expiresIn: int
