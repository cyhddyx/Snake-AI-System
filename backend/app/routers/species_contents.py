from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.services.models import Species, SpeciesContents
from app.services.db_utils import commit_or_409
from app.services.security import get_current_reviewer_user
import app.services.schemas as schemas

router = APIRouter(prefix="/species/{species_id}/content", tags=["物种详情"])


@router.post("", response_model=schemas.SpeciesContentResponse, status_code=201)
async def create_species_content(
    species_id: int,
    data: schemas.SpeciesContentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    species = await db.get(Species, species_id)
    if not species:
        raise HTTPException(404, "物种不存在")
    result = await db.execute(
        select(SpeciesContents).where(SpeciesContents.species_id == species_id)
    )
    if result.scalars().first():
        raise HTTPException(409, "该物种已有内容，请使用 PATCH 更新")
    content = SpeciesContents(**{**data.model_dump(exclude={"species_id"}), "species_id": species_id})
    db.add(content)
    await commit_or_409(db, "该物种已有内容，请使用 PATCH 更新")
    await db.refresh(content)
    return content


@router.get("", response_model=schemas.SpeciesContentResponse)
async def get_species_content(species_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SpeciesContents).where(SpeciesContents.species_id == species_id)
    )
    content = result.scalars().first()
    if not content:
        raise HTTPException(404, "该物种暂无详细内容")
    return content


@router.patch("", response_model=schemas.SpeciesContentResponse)
async def update_species_content(
    species_id: int,
    data: schemas.SpeciesContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    result = await db.execute(
        select(SpeciesContents).where(SpeciesContents.species_id == species_id)
    )
    content = result.scalars().first()
    if not content:
        raise HTTPException(404, "该物种暂无详细内容")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(content, key, value)
    await commit_or_409(db)
    await db.refresh(content)
    return content


@router.delete("", status_code=204)
async def delete_species_content(
    species_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    result = await db.execute(
        select(SpeciesContents).where(SpeciesContents.species_id == species_id)
    )
    content = result.scalars().first()
    if not content:
        raise HTTPException(404, "该物种暂无详细内容")
    await db.delete(content)
    await db.commit()
