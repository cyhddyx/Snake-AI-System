from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, text, and_, func
from app.services.database import get_db
from app.services.models import Families, Genera, Species
from app.services import schemas as s
from typing import Optional

router = APIRouter(prefix="/search", tags=["搜索"])


@router.get("", response_model=s.SearchResponse)
async def global_search(
    q: str = Query(..., description="搜索关键词", min_length=1),
    search_type: Optional[str] = Query(
        "all", description="搜索类型: species/family/genus/all"
    ),
    toxicity: Optional[str] = Query(None, description="按毒性筛选"),
    iucn_status: Optional[str] = Query(None, description="按IUCN状态筛选"),
    family_id: Optional[int] = Query(None, description="按科筛选"),
    genus_id: Optional[int] = Query(None, description="按属筛选"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    results = {"species": [], "families": [], "genera": []}
    total = {"species": 0, "families": 0, "genera": 0}

    search_pattern = f"%{q}%"
    base_conditions = [
        or_(
            Species.chinese_name.ilike(search_pattern),
            Species.latin_name.ilike(search_pattern),
            func.array_to_string(Species.aliases, " ").ilike(search_pattern),
        )
    ]

    if search_type in ("all", "species"):
        species_conditions = base_conditions.copy()
        if toxicity:
            species_conditions.append(Species.toxicity == toxicity)
        if iucn_status:
            species_conditions.append(Species.iucn_status == iucn_status)
        if family_id:
            genus_subq = select(Genera.id).where(Genera.family_id == family_id).scalar_subquery()
            species_conditions.append(Species.genus_id.in_(genus_subq))
        if genus_id:
            species_conditions.append(Species.genus_id == genus_id)

        count_stmt = select(func.count()).select_from(Species).where(and_(*species_conditions))
        total_result = await db.execute(count_stmt)
        total["species"] = total_result.scalar_one()

        stmt = (
            select(Species)
            .where(and_(*species_conditions))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        results["species"] = result.scalars().all()

    if search_type in ("all", "family"):
        family_conditions = [
            or_(
                Families.chinese_name.ilike(search_pattern),
                Families.latin_name.ilike(search_pattern),
            )
        ]
        if family_id:
            family_conditions.append(Families.id == family_id)
        if genus_id:
            family_conditions.append(
                Families.id.in_(
                    select(Genera.family_id).where(Genera.id == genus_id)
                )
            )

        count_stmt = select(func.count()).select_from(Families).where(and_(*family_conditions))
        total_result = await db.execute(count_stmt)
        total["families"] = total_result.scalar_one()

        stmt = (
            select(Families)
            .where(and_(*family_conditions))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        results["families"] = result.scalars().all()

    if search_type in ("all", "genus"):
        genus_conditions = [
            or_(
                Genera.chinese_name.ilike(search_pattern),
                Genera.latin_name.ilike(search_pattern),
            )
        ]
        if family_id:
            genus_conditions.append(Genera.family_id == family_id)
        if genus_id:
            genus_conditions.append(Genera.id == genus_id)

        count_stmt = select(func.count()).select_from(Genera).where(and_(*genus_conditions))
        total_result = await db.execute(count_stmt)
        total["genera"] = total_result.scalar_one()

        stmt = (
            select(Genera)
            .where(and_(*genus_conditions))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        results["genera"] = result.scalars().all()

    return {"results": results, "total": total}


@router.post("/init-fulltext", status_code=201)
async def init_fulltext_search(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await db.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))

        await db.execute(text("""
            ALTER TABLE families 
            ADD COLUMN IF NOT EXISTS fts_vector tsvector 
            GENERATED ALWAYS AS (
                setweight(to_tsvector('simple', coalesce(chinese_name, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(latin_name, '')), 'A')
            ) STORED
        """))

        await db.execute(text("""
            ALTER TABLE genera 
            ADD COLUMN IF NOT EXISTS fts_vector tsvector 
            GENERATED ALWAYS AS (
                setweight(to_tsvector('simple', coalesce(chinese_name, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(latin_name, '')), 'A')
            ) STORED
        """))

        await db.execute(text("""
            ALTER TABLE species 
            ADD COLUMN IF NOT EXISTS fts_vector tsvector 
            GENERATED ALWAYS AS (
                setweight(to_tsvector('simple', coalesce(chinese_name, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(latin_name, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(array_to_string(aliases, ' '), '')), 'B')
            ) STORED
        """))

        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_families_fts ON families USING GIN (fts_vector)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_genera_fts ON genera USING GIN (fts_vector)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS idx_species_fts ON species USING GIN (fts_vector)"))

        await db.commit()
        return {"message": "全文检索初始化成功"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"全文检索初始化失败: {e}") from e
