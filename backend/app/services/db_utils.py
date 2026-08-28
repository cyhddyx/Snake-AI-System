from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


async def commit_or_409(db, message: str = "数据冲突，请检查是否重复或关联数据是否存在"):
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=message) from exc
