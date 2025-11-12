# auth.py
from fastapi import APIRouter, HTTPException, Depends, Request, Header
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
import json
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Auth"])

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_REDIRECT_URL = os.getenv("GOOGLE_REDIRECT_URL", "http://localhost:8000/auth/google/callback")
SECRET_KEY = os.getenv("JWT_SECRET", "supersecret")
ALGORITHM = "HS256"

# Initialize clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# redis_client = Redis(host="localhost", port=6379, decode_responses=True) #removed this line for docker compatibility

redis_client = Redis(host="redis", port=6379, decode_responses=True)


# Session settings
SESSION_EXPIRY = 60 * 60 * 24 * 7  # 7 days in seconds
TOKEN_CACHE_EXPIRY = 60 * 60 * 2   # 2 hours in seconds

class TokenData(BaseModel):
    access_token: str


# ============ Redis Session Management ============

def cache_user_session(email: str, user_data: dict, access_token: str):
    """
    Cache user session data in Redis for fast authentication checks.
    
    Structure:
    - session:{email} -> {user_data, token, last_activity}
    - token:{access_token} -> email (for reverse lookup)
    """
    session_key = f"session:{email}"
    token_key = f"token:{access_token}"
    
    session_data = {
        "email": email,
        "name": user_data.get("name", ""),
        "google_id": user_data.get("google_id", ""),
        "access_token": access_token,
        "last_activity": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Store session data with 7-day expiry
    redis_client.setex(
        session_key,
        SESSION_EXPIRY,
        json.dumps(session_data)
    )
    
    # Store token->email mapping with 2-hour expiry (token refresh time)
    redis_client.setex(
        token_key,
        TOKEN_CACHE_EXPIRY,
        email
    )
    
    print(f"✅ Session cached for {email}")


def get_cached_session(email: str) -> Optional[dict]:
    """Retrieve cached session data for a user."""
    session_key = f"session:{email}"
    session_data = redis_client.get(session_key)
    
    if session_data:
        return json.loads(session_data)
    return None


def get_user_from_token(access_token: str) -> Optional[str]:
    """Get email from token using Redis cache (O(1) lookup)."""
    token_key = f"token:{access_token}"
    return redis_client.get(token_key)


def invalidate_session(email: str):
    """Remove user session from cache (for logout)."""
    session_key = f"session:{email}"
    
    # Get the session to find the token
    session_data = get_cached_session(email)
    if session_data:
        token_key = f"token:{session_data.get('access_token')}"
        redis_client.delete(token_key)
    
    redis_client.delete(session_key)
    print(f"🔴 Session invalidated for {email}")


def update_last_activity(email: str):
    """Update the last activity timestamp for a user session."""
    session_data = get_cached_session(email)
    if session_data:
        session_data["last_activity"] = datetime.utcnow().isoformat()
        session_key = f"session:{email}"
        redis_client.setex(
            session_key,
            SESSION_EXPIRY,
            json.dumps(session_data)
        )


def get_active_sessions_count() -> int:
    """Get count of active user sessions (for analytics)."""
    pattern = "session:*"
    return len(redis_client.keys(pattern))


# ============ Auth Endpoints ============

@router.get("/google")
def login_with_google():
    """Initiate Google OAuth flow."""
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
    """Handle Google OAuth callback and redirect to frontend."""
    frontend_url = 'https://payup-frontend-332078128555.us-central1.run.app'
    return RedirectResponse(f"{frontend_url}/auth/callback")



@router.post("/verify")
async def verify_token(data: TokenData):
    """
    Verify access token and create/cache user session.
    This is called after Google OAuth completes.
    """
    try:
        access_token = data.access_token
        
        # Check Redis cache first (fast path)
        cached_email = get_user_from_token(access_token)
        if cached_email:
            cached_session = get_cached_session(cached_email)
            if cached_session:
                update_last_activity(cached_email)
                print(f"✅ Cache hit for {cached_email}")
                return {
                    "user": {
                        "email": cached_session["email"],
                        "name": cached_session["name"]
                    }
                }
        
        # Cache miss - verify with Supabase (slow path)
        print(f"⚠️ Cache miss - verifying with Supabase...")
        user_response = supabase.auth.get_user(access_token)
        
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        email = user_response.user.email
        name = user_response.user.user_metadata.get("full_name", "")
        google_id = user_response.user.id
        
        # Save/update user in database
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            if not existing_user:
                new_user = User(email=email, name=name, google_id=google_id)
                session.add(new_user)
                await session.commit()
                print(f"✅ New user created: {email}")
            else:
                print(f"✅ Existing user found: {email}")
        
        # Cache the session in Redis
        user_data = {
            "name": name,
            "google_id": google_id
        }
        cache_user_session(email, user_data, access_token)
        
        return {"user": {"email": email, "name": name}}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Auth failed: {str(e)}")


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """
    Logout user and invalidate their session.
    Expects: Authorization: Bearer <access_token>
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="No authorization token provided")
        
        access_token = authorization.replace("Bearer ", "")
        
        # Get email from token
        email = get_user_from_token(access_token)
        if not email:
            # Token not in cache, might be expired
            return {"message": "Session already expired"}
        
        # Invalidate the session
        invalidate_session(email)
        
        return {"message": "Logged out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/session")
async def get_session(authorization: Optional[str] = Header(None)):
    """
    Get current user session info.
    Useful for checking if user is still logged in.
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="No authorization token provided")
        
        access_token = authorization.replace("Bearer ", "")
        
        # Get email from token cache
        email = get_user_from_token(access_token)
        if not email:
            raise HTTPException(status_code=401, detail="Session expired")
        
        # Get session data
        session_data = get_cached_session(email)
        if not session_data:
            raise HTTPException(status_code=401, detail="Session not found")
        
        # Update last activity
        update_last_activity(email)
        
        return {
            "user": {
                "email": session_data["email"],
                "name": session_data["name"]
            },
            "last_activity": session_data["last_activity"],
            "created_at": session_data["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Session check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Session check failed")


@router.get("/stats")
async def auth_stats():
    """
    Get authentication statistics (admin endpoint).
    Returns count of active sessions.
    """
    try:
        active_sessions = get_active_sessions_count()
        return {
            "active_sessions": active_sessions,
            "session_expiry_hours": SESSION_EXPIRY / 3600,
            "token_cache_hours": TOKEN_CACHE_EXPIRY / 3600
        }
    except Exception as e:
        print(f"❌ Stats error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get stats")


# ============ Auth Dependency (for protecting routes) ============

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to get current authenticated user.
    Use this to protect your routes.
    
    Example:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['email']}"}
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = authorization.replace("Bearer ", "")
    
    # Check Redis cache
    email = get_user_from_token(access_token)
    if not email:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    
    session_data = get_cached_session(email)
    if not session_data:
        raise HTTPException(status_code=401, detail="Session not found")
    
    # Update last activity
    update_last_activity(email)
    
    return {
        "email": session_data["email"],
        "name": session_data["name"],
        "google_id": session_data["google_id"]
    }