from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.database import get_db
from app.services.models import Users
from app.services.db_utils import commit_or_409
from app.services.security import (
    get_current_admin_user,
    get_current_user,
    hash_password,
    verify_password,
)
import app.services.schemas as schemas

router = APIRouter(prefix="/users", tags=["用户"])


def _role_value(user) -> str:
    return getattr(user.role, "value", user.role)


def _ensure_self_or_admin(current_user, target_user_id: int):
    if current_user.id != target_user_id and _role_value(current_user) != "admin":
        raise HTTPException(403, "无权访问其他用户的数据")


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
async def register_user(data: schemas.UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Users).where(
            (Users.username == data.username) | (Users.email == data.email)
        )
    )
    if result.scalars().first():
        raise HTTPException(409, "用户名或邮箱已存在")
    user = Users(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await commit_or_409(db, "用户名或邮箱已存在")
    await db.refresh(user)
    return user


@router.get("", response_model=list[schemas.UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: Users = Depends(get_current_admin_user),
):
    result = await db.execute(select(Users))
    return result.scalars().all()


@router.get("/{user_id}", response_model=schemas.UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id)
    user = await db.get(Users, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    return user


@router.patch("/{user_id}", response_model=schemas.UserResponse)
async def update_user(
    user_id: int,
    data: schemas.UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id)
    user = await db.get(Users, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    update_data = data.model_dump(exclude_unset=True)
    is_admin = _role_value(current_user) == "admin"
    if not is_admin and any(key in update_data for key in ("role", "is_active")):
        raise HTTPException(403, "无权修改角色或启用状态")
    for key, value in update_data.items():
        setattr(user, key, value)
    await commit_or_409(db, "用户名或邮箱已存在")
    await db.refresh(user)
    return user


@router.post("/{user_id}/change-password", status_code=200)
async def change_password(
    user_id: int,
    data: schemas.UserChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(403, "只能修改自己的密码")
    user = await db.get(Users, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(400, "旧密码错误")
    user.hashed_password = hash_password(data.new_password)
    await commit_or_409(db)
    return {"message": "密码修改成功"}


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_self_or_admin(current_user, user_id)
    user = await db.get(Users, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    await db.delete(user)
    await db.commit()
