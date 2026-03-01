import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.models.db_models import CategoryModel, UserModel

router = APIRouter(prefix="/categories", tags=["Categories"])


# ── Schemas ────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    slug: str
    icon: str = "category"
    description: str = ""


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    slug: str
    icon: str
    description: str
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _to_response(c: CategoryModel) -> CategoryResponse:
    return CategoryResponse(
        id=str(c.id),
        tenant_id=str(c.tenant_id),
        name=c.name,
        slug=c.slug,
        icon=c.icon,
        description=c.description,
        is_active=c.is_active,
        created_by=str(c.created_by) if c.created_by else None,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List categories for the current tenant. Non-admins only see active ones."""
    query = select(CategoryModel).where(CategoryModel.tenant_id == user.tenant_id)
    if not user.is_admin:
        query = query.where(CategoryModel.is_active == True)
    query = query.order_by(CategoryModel.created_at.asc())
    result = await db.execute(query)
    return [_to_response(c) for c in result.scalars().all()]


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreate,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin creates a new category for their tenant."""
    exists = await db.execute(
        select(CategoryModel).where(
            CategoryModel.tenant_id == admin.tenant_id,
            CategoryModel.slug == body.slug,
        )
    )
    if exists.scalars().first():
        raise HTTPException(status_code=409, detail=f"Category '{body.slug}' already exists")

    cat = CategoryModel(
        tenant_id=admin.tenant_id,
        name=body.name,
        slug=body.slug,
        icon=body.icon,
        description=body.description,
        is_active=True,
        created_by=admin.id,
    )
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return _to_response(cat)


@router.patch("/{cat_id}", response_model=CategoryResponse)
async def update_category(
    cat_id: str,
    body: CategoryUpdate,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CategoryModel).where(CategoryModel.id == uuid.UUID(cat_id))
    )
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if body.name is not None:
        cat.name = body.name
    if body.icon is not None:
        cat.icon = body.icon
    if body.description is not None:
        cat.description = body.description
    if body.is_active is not None:
        cat.is_active = body.is_active

    await db.flush()
    await db.refresh(cat)
    return _to_response(cat)


@router.delete("/{cat_id}", status_code=204)
async def delete_category(
    cat_id: str,
    admin: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CategoryModel).where(CategoryModel.id == uuid.UUID(cat_id))
    )
    cat = result.scalars().first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.flush()
