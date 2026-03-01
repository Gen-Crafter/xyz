import uuid
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.config import get_settings
from app.core.database import get_db

security = HTTPBearer(auto_error=False)
settings = get_settings()


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Legacy static-token check kept for backward compatibility."""
    if not credentials or credentials.credentials != settings.auth_token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return credentials.credentials


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
):
    """Extract the current user from a JWT Bearer token."""
    from app.models.db_models import UserModel

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(
        select(UserModel).where(UserModel.id == uuid.UUID(user_id))
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return user


async def require_admin(
    user=Depends(get_current_user),
):
    """Dependency that ensures the current user is an admin."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
