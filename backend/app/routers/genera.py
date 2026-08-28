from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.services.models import Families, Genera
from app.services.db_utils import commit_or_409
from app.services.security import get_current_reviewer_user
import app.services.schemas as schemas

router = APIRouter(prefix="/genera", tags=["属"])


@router.post("", response_model=schemas.GenusResponse, status_code=201)
async def create_genus(
    data: schemas.GenusCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    family = await db.get(Families, data.family_id)
    if not family:
        raise HTTPException(400, "关联的科不存在")
    genus = Genera(**data.model_dump())
    db.add(genus)
    await commit_or_409(db, "属拉丁名已存在")
    await db.refresh(genus)
    return genus


@router.get("", response_model=list[schemas.GenusResponse])
async def list_genera(
    family_id: int | None = Query(None, description="按科筛选"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Genera)
    if family_id is not None:
        stmt = stmt.where(Genera.family_id == family_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{genus_id}", response_model=schemas.GenusResponse)
async def get_genus(genus_id: int, db: AsyncSession = Depends(get_db)):
    genus = await db.get(Genera, genus_id)
    if not genus:
        raise HTTPException(404, "属不存在")
    return genus


@router.patch("/{genus_id}", response_model=schemas.GenusResponse)
async def update_genus(
    genus_id: int,
    data: schemas.GenusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    genus = await db.get(Genera, genus_id)
    if not genus:
        raise HTTPException(404, "属不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "family_id" in update_data:
        if update_data["family_id"] is None:
            raise HTTPException(400, "关联的科不能为空")
        if not await db.get(Families, update_data["family_id"]):
            raise HTTPException(400, "关联的科不存在")
    for key, value in update_data.items():
        setattr(genus, key, value)
    await commit_or_409(db, "属拉丁名已存在")
    await db.refresh(genus)
    return genus


@router.delete("/{genus_id}", status_code=204)
async def delete_genus(
    genus_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    genus = await db.get(Genera, genus_id)
    if not genus:
        raise HTTPException(404, "属不存在")
    await db.delete(genus)
    await commit_or_409(db, "该属下仍有关联的物种，不能删除")
