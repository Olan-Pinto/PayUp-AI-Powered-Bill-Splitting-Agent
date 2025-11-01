# auth.py
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
import supabase
from supabase import create_client, Client
import os
from redis import Redis
import jwt
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models import User

router = APIRouter(prefix="/auth", tags=["Auth"])

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_REDIRECT_URL = os.getenv("GOOGLE_REDIRECT_URL", "http://localhost:8000/auth/google/callback")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

redis_client = Redis(host="localhost", port=6379, decode_responses=True)

SECRET_KEY = os.getenv("JWT_SECRET", "supersecret")
ALGORITHM = "HS256"

class TokenData(BaseModel):
    access_token: str

def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(hours=2)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


@router.get("/google")
def login_with_google():
    redirect_url = os.getenv("GOOGLE_REDIRECT_URL", "http://localhost:8000/auth/google/callback")
    authorize_url = (
        f"{SUPABASE_URL}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={redirect_url}"
        f"&flow_type=pkce"
        f"&scopes=openid%20email%20profile"
    )
    return RedirectResponse(authorize_url)


@router.get("/google/callback")
async def google_callback(request: Request):
    # Just redirect to frontend - it will handle the hash fragment
    return RedirectResponse("http://localhost:5173/auth/callback")


@router.post("/verify")
async def verify_token(data: TokenData):
    try:
        print(f"Verifying token: {data.access_token[:20]}...")  # Log first 20 chars
        
        user_response = supabase.auth.get_user(data.access_token)
        print(f"Supabase response: {user_response}")
        
        if not user_response or not user_response.user:
            print("No user found in response")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        email = user_response.user.email
        name = user_response.user.user_metadata.get("full_name", "")
        google_id = user_response.user.id
        
        print(f"User verified: {email}")
        
        # Save user in DB if new
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            if not existing_user:
                new_user = User(email=email, name=name, google_id=google_id)
                session.add(new_user)
                await session.commit()
                print(f"New user created: {email}")
            else:
                print(f"Existing user found: {email}")
        
        # Cache token in Redis
        # redis_client.setex(f"user_session:{email}", timedelta(hours=2), data.access_token)
        
        return {"user": {"email": email, "name": name}}
        
    except Exception as e:
        print(f"Verification error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Auth failed: {str(e)}")