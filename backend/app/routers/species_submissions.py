from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.schemas as schemas
from app.services.database import get_db
from app.services.db_utils import commit_or_409
from app.services.models import Genera, Species, SpeciesContents, SpeciesImages, SpeciesSubmissions, Users
from app.services.security import get_current_user


router = APIRouter(prefix="/species-submissions", tags=["物种投稿"])


def _role_value(user) -> str:
    return getattr(user.role, "value", user.role)


def _ensure_reviewer(current_user):
    if _role_value(current_user) not in {"admin", "editor"}:
        raise HTTPException(403, "仅管理员或编辑可审核投稿")


def _ensure_submission_author(current_user: Users, submission: SpeciesSubmissions):
    if submission.submitter_id != current_user.id:
        raise HTTPException(403, "无权操作其他用户投稿")


def _ensure_submission_pending(submission: SpeciesSubmissions):
    if submission.status != "pending":
        raise HTTPException(409, "仅待审核投稿允许修改或撤回")


def _normalize_submission_images(images: list[schemas.SubmissionImageCreate | dict] | None) -> list[dict]:
    if not images:
        return []

    normalized = []
    has_cover = False
    for index, image in enumerate(images):
        item = image.model_dump() if hasattr(image, "model_dump") else dict(image)
        item["sort_order"] = item.get("sort_order") if item.get("sort_order") is not None else index
        item["image_type"] = item.get("image_type") or "overview"
        item["is_cover"] = bool(item.get("is_cover"))
        if item["is_cover"]:
            if has_cover:
                item["is_cover"] = False
            else:
                has_cover = True
        normalized.append(item)

    if normalized and not has_cover:
        normalized[0]["is_cover"] = True
    return normalized


@router.post("", response_model=schemas.SpeciesSubmissionResponse, status_code=201)
async def create_submission(
    data: schemas.SpeciesSubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    genus = await db.get(Genera, data.genus_id)
    if not genus:
        raise HTTPException(400, "关联的属不存在")

    submission = SpeciesSubmissions(
        submitter_id=current_user.id,
        **data.model_dump(exclude={"images"}),
        images=_normalize_submission_images(data.images),
    )
    db.add(submission)
    await commit_or_409(db, "投稿保存失败，可能存在重复数据")
    await db.refresh(submission)
    return submission


@router.patch("/{submission_id}", response_model=schemas.SpeciesSubmissionResponse)
async def update_submission(
    submission_id: int,
    data: schemas.SpeciesSubmissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    submission = await db.get(SpeciesSubmissions, submission_id)
    if not submission:
        raise HTTPException(404, "投稿不存在")

    _ensure_submission_author(current_user, submission)
    _ensure_submission_pending(submission)

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return submission

    genus_id = update_data.get("genus_id")
    if genus_id is not None:
        genus = await db.get(Genera, genus_id)
        if not genus:
            raise HTTPException(400, "关联的属不存在")

    for key, value in update_data.items():
        if key == "images":
            setattr(submission, key, _normalize_submission_images(value))
        else:
            setattr(submission, key, value)
    submission.updated_at = datetime.now(timezone.utc)

    await commit_or_409(db, "投稿更新失败，可能存在重复数据")
    await db.refresh(submission)
    return submission


@router.delete("/{submission_id}", status_code=204)
async def delete_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    submission = await db.get(SpeciesSubmissions, submission_id)
    if not submission:
        raise HTTPException(404, "投稿不存在")

    _ensure_submission_author(current_user, submission)
    _ensure_submission_pending(submission)

    await db.delete(submission)
    await db.commit()


@router.get("", response_model=list[schemas.SpeciesSubmissionResponse])
async def list_submissions(
    status: schemas.SubmissionStatus | None = Query(None),
    mine_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    stmt = select(SpeciesSubmissions).order_by(SpeciesSubmissions.created_at.desc())

    if mine_only or _role_value(current_user) == "user":
        stmt = stmt.where(SpeciesSubmissions.submitter_id == current_user.id)

    if status is not None:
        stmt = stmt.where(SpeciesSubmissions.status == status.value)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{submission_id}", response_model=schemas.SpeciesSubmissionResponse)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    submission = await db.get(SpeciesSubmissions, submission_id)
    if not submission:
        raise HTTPException(404, "投稿不存在")
    if _role_value(current_user) == "user" and submission.submitter_id != current_user.id:
        raise HTTPException(403, "无权查看其他用户投稿")
    return submission


@router.post("/{submission_id}/approve", response_model=schemas.SpeciesSubmissionResponse)
async def approve_submission(
    submission_id: int,
    data: schemas.SpeciesSubmissionReview,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_reviewer(current_user)
    submission = await db.get(SpeciesSubmissions, submission_id)
    if not submission:
        raise HTTPException(404, "投稿不存在")
    if submission.status != "pending":
        raise HTTPException(409, "该投稿已处理")

    review_time = datetime.now(timezone.utc)
    try:
        if submission.target_species_id:
            existing_species = await db.get(Species, submission.target_species_id)
            if not existing_species:
                raise HTTPException(404, "纠错目标物种不存在")

            correction_data = {
                k: v for k, v in [
                    ("genus_id", submission.genus_id),
                    ("chinese_name", submission.chinese_name),
                    ("latin_name", submission.latin_name),
                    ("aliases", submission.aliases),
                    ("toxicity", submission.toxicity),
                    ("iucn_status", submission.iucn_status),
                    ("discoverer", submission.discoverer),
                    ("discover_year", submission.discover_year),
                    ("basic_intro", submission.basic_intro),
                    ("measurements", submission.measurements),
                ] if v is not None
            }
            for key, value in correction_data.items():
                setattr(existing_species, key, value)

            has_content = any(
                [submission.zoology, submission.history, submission.morphology,
                 submission.distribution, submission.habitat, submission.behavior,
                 submission.reproduction, submission.conservation, submission.value,
                 submission.hazard]
            )
            if has_content:
                result = await db.execute(
                    select(SpeciesContents).where(
                        SpeciesContents.species_id == submission.target_species_id
                    )
                )
                existing_content = result.scalars().first()
                if existing_content:
                    content_fields = {
                        k: v for k, v in [
                            ("zoology", submission.zoology), ("history", submission.history),
                            ("morphology", submission.morphology), ("distribution", submission.distribution),
                            ("habitat", submission.habitat), ("behavior", submission.behavior),
                            ("reproduction", submission.reproduction), ("conservation", submission.conservation),
                            ("value", submission.value), ("hazard", submission.hazard),
                        ] if v is not None
                    }
                    for key, value in content_fields.items():
                        setattr(existing_content, key, value)
                else:
                    db.add(SpeciesContents(
                        species_id=submission.target_species_id,
                        zoology=submission.zoology, history=submission.history,
                        morphology=submission.morphology, distribution=submission.distribution,
                        habitat=submission.habitat, behavior=submission.behavior,
                        reproduction=submission.reproduction, conservation=submission.conservation,
                        value=submission.value, hazard=submission.hazard,
                        content_format=submission.content_format,
                    ))

            submission_images = _normalize_submission_images(submission.images or [])
            if submission_images:
                result = await db.execute(
                    select(SpeciesImages).where(
                        SpeciesImages.species_id == submission.target_species_id
                    )
                )
                await db.flush()
                for image in submission_images:
                    db.add(SpeciesImages(
                        species_id=submission.target_species_id,
                        image_url=image["image_url"],
                        thumbnail_url=image.get("thumbnail_url"),
                        caption=image.get("caption"),
                        photographer=image.get("photographer"),
                        image_type=image.get("image_type") or "overview",
                        sort_order=image.get("sort_order") or 0,
                        is_cover=bool(image.get("is_cover")),
                    ))

            submission.created_species_id = submission.target_species_id
        else:
            species = Species(
                genus_id=submission.genus_id,
                chinese_name=submission.chinese_name,
                latin_name=submission.latin_name,
                aliases=submission.aliases,
                toxicity=submission.toxicity,
                iucn_status=submission.iucn_status,
                discoverer=submission.discoverer,
                discover_year=submission.discover_year,
                basic_intro=submission.basic_intro,
                measurements=submission.measurements,
            )
            db.add(species)
            await db.flush()

            has_content = any(
                [
                    submission.zoology,
                    submission.history,
                    submission.morphology,
                    submission.distribution,
                    submission.habitat,
                    submission.behavior,
                    submission.reproduction,
                    submission.conservation,
                    submission.value,
                    submission.hazard,
                ]
            )
            if has_content:
                db.add(
                    SpeciesContents(
                        species_id=species.id,
                        zoology=submission.zoology,
                        history=submission.history,
                        morphology=submission.morphology,
                        distribution=submission.distribution,
                        habitat=submission.habitat,
                        behavior=submission.behavior,
                        reproduction=submission.reproduction,
                        conservation=submission.conservation,
                        value=submission.value,
                        hazard=submission.hazard,
                        content_format=submission.content_format,
                    )
                )

            submission_images = _normalize_submission_images(submission.images or [])
            for image in submission_images:
                db.add(
                    SpeciesImages(
                        species_id=species.id,
                        image_url=image["image_url"],
                        thumbnail_url=image.get("thumbnail_url"),
                        caption=image.get("caption"),
                        photographer=image.get("photographer"),
                        image_type=image.get("image_type") or "overview",
                        sort_order=image.get("sort_order") or 0,
                        is_cover=bool(image.get("is_cover")),
                    )
                )

            submission.created_species_id = species.id

        submission.status = "approved"
        submission.review_note = data.review_note
        submission.reviewer_id = current_user.id
        submission.reviewed_at = review_time
        submission.updated_at = review_time

        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="投稿通过失败，数据保存异常或物种拉丁名已存在",
        ) from exc

    await db.refresh(submission)
    return submission


@router.post("/{submission_id}/reject", response_model=schemas.SpeciesSubmissionResponse)
async def reject_submission(
    submission_id: int,
    data: schemas.SpeciesSubmissionReview,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    _ensure_reviewer(current_user)
    submission = await db.get(SpeciesSubmissions, submission_id)
    if not submission:
        raise HTTPException(404, "投稿不存在")
    if submission.status != "pending":
        raise HTTPException(409, "该投稿已处理")

    submission.status = "rejected"
    submission.review_note = data.review_note
    submission.reviewer_id = current_user.id
    review_time = datetime.now(timezone.utc)
    submission.reviewed_at = review_time
    submission.updated_at = review_time
    await commit_or_409(db)
    await db.refresh(submission)
    return submission
