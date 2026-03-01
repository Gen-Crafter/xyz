import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_user, require_admin
from app.models.db_models import UserModel, TenantModel

# ── Password hashing ──────────────────────────────────────────────────────
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── JWT ────────────────────────────────────────────────────────────────────
from jose import jwt, JWTError

settings = get_settings()

router = APIRouter(prefix="/users", tags=["User Management"])


# ── Schemas ────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str
    is_admin: bool = False
    tenant_id: Optional[str] = None  # if omitted, uses default tenant


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: Optional[str] = None
    is_admin: bool = False
    tenant_id: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────────────────

def _create_token(user: UserModel) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id),
        "is_admin": user.is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_exp_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def _get_or_create_default_tenant(db: AsyncSession) -> uuid.UUID:
    result = await db.execute(select(TenantModel).where(TenantModel.name == "default"))
    tenant = result.scalars().first()
    if tenant:
        return tenant.id
    t = TenantModel(name="default")
    db.add(t)
    await db.flush()
    return t.id


# ── Auth Endpoints ─────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate
    exists = await db.execute(select(UserModel).where(UserModel.email == body.email))
    if exists.scalars().first():
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant_id = uuid.UUID(body.tenant_id) if body.tenant_id else await _get_or_create_default_tenant(db)

    user = UserModel(
        email=body.email,
        full_name=body.full_name,
        hashed_password=pwd_ctx.hash(body.password),
        is_admin=body.is_admin,
        tenant_id=tenant_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = _create_token(user)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        tenant_id=str(user.tenant_id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserModel).where(UserModel.email == body.email))
    user = result.scalars().first()
    if not user or not pwd_ctx.verify(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = _create_token(user)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_admin=user.is_admin,
        tenant_id=str(user.tenant_id),
    )


# ── Profile Endpoints ─────────────────────────────────────────────────────

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    user: UserModel = Depends(get_current_user),
):
    return UserResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        is_active=user.is_active, is_admin=user.is_admin,
        tenant_id=str(user.tenant_id),
        created_at=user.created_at, updated_at=user.updated_at,
    )


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdate,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name is not None:
        user.full_name = body.full_name
    await db.flush()
    await db.refresh(user)
    return UserResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        is_active=user.is_active, is_admin=user.is_admin,
        tenant_id=str(user.tenant_id),
        created_at=user.created_at, updated_at=user.updated_at,
    )


@router.post("/profile/change-password")
async def change_password(
    body: PasswordChange,
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not pwd_ctx.verify(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = pwd_ctx.hash(body.new_password)
    await db.flush()
    return {"message": "Password changed successfully"}


# ── Admin: User Management ─────────────────────────────────────────────────

@router.get("", response_model=list[UserResponse])
async def list_users(
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserModel)
        .where(UserModel.tenant_id == admin.tenant_id)
        .order_by(UserModel.created_at.desc())
    )
    users = result.scalars().all()
    return [
        UserResponse(
            id=str(u.id), email=u.email, full_name=u.full_name,
            is_active=u.is_active, is_admin=u.is_admin,
            tenant_id=str(u.tenant_id),
            created_at=u.created_at, updated_at=u.updated_at,
        )
        for u in users
    ]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    exists = await db.execute(select(UserModel).where(UserModel.email == body.email))
    if exists.scalars().first():
        raise HTTPException(status_code=409, detail="Email already registered")

    tenant_id = admin.tenant_id

    user = UserModel(
        email=body.email,
        full_name=body.full_name,
        hashed_password=pwd_ctx.hash(body.password),
        is_admin=body.is_admin,
        tenant_id=tenant_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        is_active=user.is_active, is_admin=user.is_admin,
        tenant_id=str(user.tenant_id),
        created_at=user.created_at, updated_at=user.updated_at,
    )


@router.patch("/{uid}", response_model=UserResponse)
async def update_user(
    uid: str,
    body: UserUpdate,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserModel).where(UserModel.id == uuid.UUID(uid)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_admin is not None:
        user.is_admin = body.is_admin

    await db.flush()
    await db.refresh(user)
    return UserResponse(
        id=str(user.id), email=user.email, full_name=user.full_name,
        is_active=user.is_active, is_admin=user.is_admin,
        tenant_id=str(user.tenant_id),
        created_at=user.created_at, updated_at=user.updated_at,
    )


@router.delete("/{uid}", status_code=204)
async def delete_user(
    uid: str,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserModel).where(UserModel.id == uuid.UUID(uid)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await db.delete(user)
    await db.flush()


@router.get("/stats")
async def user_stats(
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count(UserModel.id)))).scalar() or 0
    active = (await db.execute(select(func.count(UserModel.id)).where(UserModel.is_active == True))).scalar() or 0
    admins = (await db.execute(select(func.count(UserModel.id)).where(UserModel.is_admin == True))).scalar() or 0
    tenants = (await db.execute(select(func.count(TenantModel.id)))).scalar() or 0
    return {"total_users": total, "active_users": active, "admin_users": admins, "tenants": tenants}
