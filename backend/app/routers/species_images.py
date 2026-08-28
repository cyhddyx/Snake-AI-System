from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.services.models import Species, SpeciesImages
from app.services.db_utils import commit_or_409
from app.services.security import get_current_reviewer_user
import app.services.schemas as schemas

router = APIRouter(tags=["物种图片"])


@router.post(
    "/species/{species_id}/images",
    response_model=schemas.SpeciesImageResponse,
    status_code=201,
)
async def create_species_image(
    species_id: int,
    data: schemas.SpeciesImageCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    species = await db.get(Species, species_id)
    if not species:
        raise HTTPException(404, "物种不存在")
    image = SpeciesImages(**{**data.model_dump(exclude={"species_id"}), "species_id": species_id})
    db.add(image)
    await commit_or_409(db)
    await db.refresh(image)
    return image


@router.get(
    "/species/{species_id}/images",
    response_model=list[schemas.SpeciesImageResponse],
)
async def list_species_images(species_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SpeciesImages)
        .where(SpeciesImages.species_id == species_id)
        .order_by(SpeciesImages.sort_order)
    )
    return result.scalars().all()


@router.patch("/images/{image_id}", response_model=schemas.SpeciesImageResponse)
async def update_image(
    image_id: int,
    data: schemas.SpeciesImageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    image = await db.get(SpeciesImages, image_id)
    if not image:
        raise HTTPException(404, "图片不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(image, key, value)
    await commit_or_409(db)
    await db.refresh(image)
    return image


@router.delete("/images/{image_id}", status_code=204)
async def delete_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_reviewer_user),
):
    image = await db.get(SpeciesImages, image_id)
    if not image:
        raise HTTPException(404, "图片不存在")
    await db.delete(image)
    await db.commit()
