from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update
from app.services.database import get_db
from app.services.models import Genera, Species
from app.services.db_utils import commit_or_409
from app.services.security import get_current_reviewer_user
import app.services.schemas as schemas

router = APIRouter(prefix="/species", tags=["物种"])


@router.post("", response_model=schemas.SpeciesResponse, status_code=201)
async def create_species(
    data: schemas.SpeciesCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    genus = await db.get(Genera, data.genus_id)
    if not genus:
        raise HTTPException(400, "关联的属不存在")
    species = Species(**data.model_dump())
    db.add(species)
    await commit_or_409(db, "物种拉丁名已存在")
    await db.refresh(species)
    return species


@router.get("", response_model=list[schemas.SpeciesResponse])
async def list_species(
    genus_id: int | None = Query(None, description="按属筛选"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Species).order_by(Species.chinese_name.asc(), Species.latin_name.asc(), Species.id.asc())
    if genus_id is not None:
        stmt = stmt.where(Species.genus_id == genus_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{species_id}", response_model=schemas.SpeciesResponse)
async def get_species(species_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Species)
        .where(Species.id == species_id)
        .values(view_count=func.coalesce(Species.view_count, 0) + 1)
        .returning(Species.id)
    )
    updated_species_id = result.scalar_one_or_none()
    if not updated_species_id:
        raise HTTPException(404, "物种不存在")
    await commit_or_409(db)
    species = await db.get(Species, species_id)
    return species


@router.patch("/{species_id}", response_model=schemas.SpeciesResponse)
async def update_species(
    species_id: int,
    data: schemas.SpeciesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    species = await db.get(Species, species_id)
    if not species:
        raise HTTPException(404, "物种不存在")
    update_data = data.model_dump(exclude_unset=True)
    if "genus_id" in update_data:
        if update_data["genus_id"] is None:
            raise HTTPException(400, "关联的属不能为空")
        if not await db.get(Genera, update_data["genus_id"]):
            raise HTTPException(400, "关联的属不存在")
    for key, value in update_data.items():
        setattr(species, key, value)
    await commit_or_409(db, "物种拉丁名已存在")
    await db.refresh(species)
    return species


@router.delete("/{species_id}", status_code=204)
async def delete_species(
    species_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    species = await db.get(Species, species_id)
    if not species:
        raise HTTPException(404, "物种不存在")
    await db.delete(species)
    await db.commit()
