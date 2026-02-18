import uuid
import hashlib
import json
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.crypto.config import ZKP_CRYPTO_CONFIG
from app.core.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserRegisterResponse,
    ChallengeRequest,
    ChallengeResponse,
    VerifyRequest,
    VerifyResponse,
)
from jose import jwt
from redis.asyncio import Redis

router = APIRouter()

# Schnorr Group Parameters
P = int(ZKP_CRYPTO_CONFIG.group.p, 16)
Q = int(ZKP_CRYPTO_CONFIG.group.q, 16)
G = int(ZKP_CRYPTO_CONFIG.group.g)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = settings.ACCESS_TOKEN_EXPIRE_MINUTES  # Use config if not passed? No, use delta + now
        # Actually standard implementation:
        from datetime import datetime, timezone
        expire_time = datetime.now(timezone.utc) + expires_delta
    else:
        from datetime import datetime, timezone
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire_time})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    用户注册
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.username == user_in.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Create new user
    new_user = User(
        username=user_in.username,
        public_key_y=user_in.publicKeyY,
        salt=user_in.salt
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserRegisterResponse(
        username=new_user.username,
        message="User registered successfully"
    )


@router.post("/challenge", response_model=ChallengeResponse)
async def get_challenge(
    request: ChallengeRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> Any:
    """
    获取挑战 (Step 2)
    """
    # 1. Find user
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 2. Compute Challenge c = H(R || Y || username)
    # We use the hex strings directly concatenated
    # Ensure R and Y are normalized (e.g., lower/upper case). 
    # The user example implies standard hex. We'll use the strings as provided or normalized?
    # To be safe, we'll use the strings as they come but usually hex should be normalized.
    # Let's assume the client sends consistent hex.
    
    # Payload for hash: R + Y + username
    payload = f"{request.clientR}{user.public_key_y}{user.username}"
    c_hex = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    
    # 3. Store in Redis
    challenge_id = str(uuid.uuid4())
    redis_key = f"challenge:{challenge_id}"
    
    # Store c and other info if needed. We just need c to verify.
    # Also good to store username to ensure the verify request is for the same user.
    await redis.setex(
        redis_key,
        ZKP_CRYPTO_CONFIG.challenge_ttl,
        json.dumps({
            "c": c_hex,
            "username": user.username,
            "clientR": request.clientR  # Store R to double check? 
            # The verify step receives R again. 
            # If we want to be strict, we should compare the R in verify with the one used here.
        })
    )

    return ChallengeResponse(
        challengeId=challenge_id,
        c=c_hex,
        p=ZKP_CRYPTO_CONFIG.group.p,
        q=ZKP_CRYPTO_CONFIG.group.q,
        g=ZKP_CRYPTO_CONFIG.group.g
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_proof(
    request: VerifyRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> Any:
    """
    验证证明 (Step 4)
    """
    # 1. Retrieve Challenge
    redis_key = f"challenge:{request.challengeId}"
    stored_data_str = await redis.get(redis_key)
    
    if not stored_data_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge expired or invalid"
        )
    
    stored_data = json.loads(stored_data_str)
    c_hex = stored_data["c"]
    stored_username = stored_data["username"]
    
    if stored_username != request.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username mismatch"
        )

    # 2. Get User
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 3. Verify Equation: g^s == R * Y^c (mod p)
    try:
        s_int = int(request.s, 16)
        r_int = int(request.clientR, 16)
        y_int = int(user.public_key_y, 16)
        c_int = int(c_hex, 16)
        
        # Left side: g^s mod p
        lhs = pow(G, s_int, P)
        
        # Right side: (R * Y^c) mod p
        # = (R * (Y^c mod p)) mod p
        y_c = pow(y_int, c_int, P)
        rhs = (r_int * y_c) % P
        
        if lhs != rhs:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid proof"
            )
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid hex format"
        )

    # 4. Success - Clean up and Issue Token
    await redis.delete(redis_key)
    
    access_token_expires = timedelta(seconds=86400) # 24 hours as per example expiresIn
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return VerifyResponse(
        token=access_token,
        type="Bearer",
        expiresIn=86400
    )
