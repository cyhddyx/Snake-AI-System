from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.services.models import Families
from app.services.db_utils import commit_or_409
from app.services.security import get_current_reviewer_user
import app.services.schemas as schemas

router = APIRouter(prefix="/families", tags=["科"])


@router.post("", response_model=schemas.FamilyResponse, status_code=201)
async def create_family(
    data: schemas.FamilyCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    family = Families(**data.model_dump())
    db.add(family)
    await commit_or_409(db, "科拉丁名已存在")
    await db.refresh(family)
    return family


@router.get("", response_model=list[schemas.FamilyResponse])
async def list_families(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Families))
    return result.scalars().all()


@router.get("/{family_id}", response_model=schemas.FamilyResponse)
async def get_family(family_id: int, db: AsyncSession = Depends(get_db)):
    family = await db.get(Families, family_id)
    if not family:
        raise HTTPException(404, "科不存在")
    return family


@router.patch("/{family_id}", response_model=schemas.FamilyResponse)
async def update_family(
    family_id: int,
    data: schemas.FamilyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    family = await db.get(Families, family_id)
    if not family:
        raise HTTPException(404, "科不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(family, key, value)
    await commit_or_409(db, "科拉丁名已存在")
    await db.refresh(family)
    return family


@router.delete("/{family_id}", status_code=204)
async def delete_family(
    family_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    family = await db.get(Families, family_id)
    if not family:
        raise HTTPException(404, "科不存在")
    await db.delete(family)
    await commit_or_409(db, "该科下仍有关联的属，不能删除")
