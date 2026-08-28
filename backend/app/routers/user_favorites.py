from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.services.models import Users, Species, UserFavorites
from app.services.db_utils import commit_or_409
from app.services.security import get_current_user
import app.services.schemas as schemas

router = APIRouter(tags=["收藏"])


def _role_value(user) -> str:
    return getattr(user.role, "value", user.role)


def _ensure_self_or_admin(current_user, target_user_id: int):
    if current_user.id != target_user_id and _role_value(current_user) != "admin":
        raise HTTPException(403, "无权访问其他用户的数据")


@router.post(
    "/users/{user_id}/favorites",
    response_model=schemas.UserFavoriteResponse,
    status_code=201,
)
async def add_favorite(
    user_id: int,
    data: schemas.UserFavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id)
    user = await db.get(Users, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    species = await db.get(Species, data.species_id)
    if not species:
        raise HTTPException(404, "物种不存在")
    result = await db.execute(
        select(UserFavorites).where(
            (UserFavorites.user_id == user_id)
            & (UserFavorites.species_id == data.species_id)
        )
    )
    if result.scalars().first():
        raise HTTPException(409, "已收藏该物种")
    fav = UserFavorites(user_id=user_id, species_id=data.species_id)
    db.add(fav)
    await commit_or_409(db, "已收藏该物种")
    await db.refresh(fav)
    return fav


@router.get(
    "/users/{user_id}/favorites",
    response_model=list[schemas.UserFavoriteWithSpeciesResponse],
)
async def list_favorites(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id)
    user = await db.get(Users, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    result = await db.execute(
        select(UserFavorites)
        .where(UserFavorites.user_id == user_id)
        .order_by(UserFavorites.created_at.desc())
    )
    favorites = result.scalars().all()
    resp = []
    for fav in favorites:
        species = await db.get(Species, fav.species_id)
        resp.append(
            schemas.UserFavoriteWithSpeciesResponse(
                id=fav.id,
                user_id=fav.user_id,
                species_id=fav.species_id,
                species=schemas.SpeciesResponse.model_validate(species),
                created_at=fav.created_at,
            )
        )
    return resp


@router.delete("/users/{user_id}/favorites/{species_id}", status_code=204)
async def remove_favorite(
    user_id: int,
    species_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id)
    result = await db.execute(
        select(UserFavorites).where(
            (UserFavorites.user_id == user_id)
            & (UserFavorites.species_id == species_id)
        )
    )
    fav = result.scalars().first()
    if not fav:
        raise HTTPException(404, "未收藏该物种")
    await db.delete(fav)
    await db.commit()


@router.get("/users/{user_id}/favorites/check/{species_id}")
async def check_favorite(
    user_id: int,
    species_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id)
    result = await db.execute(
        select(UserFavorites).where(
            (UserFavorites.user_id == user_id)
            & (UserFavorites.species_id == species_id)
        )
    )
    return {"is_favorited": result.scalars().first() is not None}
