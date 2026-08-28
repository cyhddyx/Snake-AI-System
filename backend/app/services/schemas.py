from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum as PyEnum


class IUCNStatus(str, PyEnum):
    EX = "EX"   # 灭绝
    EW = "EW"   # 野外灭绝
    CR = "CR"   # 极危
    EN = "EN"   # 濒危
    VU = "VU"   # 易危
    NT = "NT"   # 近危
    LC = "LC"   # 无危
    DD = "DD"   # 数据缺乏
    NE = "NE"   # 未评估
class ToxicityLevel(str, PyEnum):
    NONE = "无毒"
    MILD = "微毒"
    TOXIC = "有毒"
    SEVERE = "剧毒"
    EXTREME = "极毒"

class UserRole(str, PyEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    USER = "user"

class SubmissionStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
# ==================== Families ====================
class FamilyCreate(BaseModel):
    chinese_name: str = Field(max_length=100)
    latin_name: str = Field(max_length=150)
    description: Optional[str] = None
class FamilyUpdate(BaseModel):
    chinese_name: Optional[str] = Field(None, max_length=100)
    latin_name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
class FamilyResponse(BaseModel):
    id: int
    chinese_name: str
    latin_name: str
    description: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True
# ==================== Genera ====================
class GenusCreate(BaseModel):
    family_id: int
    chinese_name: str = Field(max_length=100)
    latin_name: str = Field(max_length=150)
    description: Optional[str] = None
class GenusUpdate(BaseModel):
    family_id: Optional[int] = None
    chinese_name: Optional[str] = Field(None, max_length=100)
    latin_name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
class GenusResponse(BaseModel):
    id: int
    family_id: int
    chinese_name: str
    latin_name: str
    description: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True
# ==================== Species ====================
class SpeciesCreate(BaseModel):
    genus_id: int
    chinese_name: str = Field(max_length=100)
    latin_name: str = Field(max_length=150)
    aliases: Optional[list[str]] = None
    toxicity: Optional[ToxicityLevel] = None
    iucn_status: Optional[IUCNStatus] = None
    discoverer: Optional[str] = Field(None, max_length=100)
    discover_year: Optional[int] = None
    basic_intro: Optional[str] = None
    measurements: Optional[dict] = None
class SpeciesUpdate(BaseModel):
    genus_id: Optional[int] = None
    chinese_name: Optional[str] = Field(None, max_length=100)
    latin_name: Optional[str] = Field(None, max_length=150)
    aliases: Optional[list[str]] = None
    toxicity: Optional[ToxicityLevel] = None
    iucn_status: Optional[IUCNStatus] = None
    discoverer: Optional[str] = Field(None, max_length=100)
    discover_year: Optional[int] = None
    basic_intro: Optional[str] = None
    measurements: Optional[dict] = None
class SpeciesResponse(BaseModel):
    id: int
    genus_id: int
    chinese_name: str
    latin_name: str
    aliases: Optional[list[str]] = None
    toxicity: Optional[ToxicityLevel] = None
    iucn_status: Optional[IUCNStatus] = None
    discoverer: Optional[str] = None
    discover_year: Optional[int] = None
    basic_intro: Optional[str] = None
    measurements: Optional[dict] = None
    view_count: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
# ==================== SpeciesContents ====================
class SpeciesContentCreate(BaseModel):
    species_id: Optional[int] = None
    zoology: Optional[str] = None
    history: Optional[str] = None
    morphology: Optional[str] = None
    distribution: Optional[str] = None
    habitat: Optional[str] = None
    behavior: Optional[str] = None
    reproduction: Optional[str] = None
    conservation: Optional[str] = None
    value: Optional[str] = None
    hazard: Optional[str] = None
    content_format: Optional[str] = "markdown"
class SpeciesContentUpdate(BaseModel):
    zoology: Optional[str] = None
    history: Optional[str] = None
    morphology: Optional[str] = None
    distribution: Optional[str] = None
    habitat: Optional[str] = None
    behavior: Optional[str] = None
    reproduction: Optional[str] = None
    conservation: Optional[str] = None
    value: Optional[str] = None
    hazard: Optional[str] = None
    content_format: Optional[str] = None
class SpeciesContentResponse(BaseModel):
    id: int
    species_id: int
    zoology: Optional[str] = None
    history: Optional[str] = None
    morphology: Optional[str] = None
    distribution: Optional[str] = None
    habitat: Optional[str] = None
    behavior: Optional[str] = None
    reproduction: Optional[str] = None
    conservation: Optional[str] = None
    value: Optional[str] = None
    hazard: Optional[str] = None
    content_format: str
    updated_at: datetime
    class Config:
        from_attributes = True
# ==================== SpeciesImages ====================
class SpeciesImageCreate(BaseModel):
    species_id: Optional[int] = None
    image_url: str = Field(max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    caption: Optional[str] = Field(None, max_length=255)
    photographer: Optional[str] = Field(None, max_length=100)
    image_type: Optional[str] = "overview"
    sort_order: Optional[int] = 0
    is_cover: Optional[bool] = False
class SpeciesImageUpdate(BaseModel):
    image_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    caption: Optional[str] = Field(None, max_length=255)
    photographer: Optional[str] = Field(None, max_length=100)
    image_type: Optional[str] = None
    sort_order: Optional[int] = None
    is_cover: Optional[bool] = None
class SpeciesImageResponse(BaseModel):
    id: int
    species_id: int
    image_url: str
    thumbnail_url: Optional[str] = None
    caption: Optional[str] = None
    photographer: Optional[str] = None
    image_type: str
    sort_order: int
    is_cover: bool
    created_at: datetime
    class Config:
        from_attributes = True


# ==================== Users ====================
class UserRegister(BaseModel):
    username: str = Field(max_length=50)
    email: str = Field(max_length=150)
    password: str = Field(min_length=6, max_length=100)

class UserCreate(BaseModel):
    username: str = Field(max_length=50)
    email: str = Field(max_length=150)
    password: str = Field(min_length=6, max_length=100)
    role: Optional[UserRole] = UserRole.USER

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=150)
    avatar_url: Optional[str] = Field(None, max_length=500)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=100)

class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=6, max_length=100)

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class SubmissionImageBase(BaseModel):
    image_url: str = Field(max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    caption: Optional[str] = Field(None, max_length=255)
    photographer: Optional[str] = Field(None, max_length=100)
    image_type: Optional[str] = "overview"
    sort_order: Optional[int] = 0
    is_cover: Optional[bool] = False


class SubmissionImageCreate(SubmissionImageBase):
    pass


class SubmissionImageResponse(SubmissionImageBase):
    image_type: str = "overview"
    sort_order: int = 0
    is_cover: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ==================== UserFavorites ====================
class UserFavoriteCreate(BaseModel):
    species_id: int

class UserFavoriteResponse(BaseModel):
    id: int
    user_id: int
    species_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class UserFavoriteWithSpeciesResponse(BaseModel):
    id: int
    user_id: int
    species_id: int
    species: SpeciesResponse
    created_at: datetime
    class Config:
        from_attributes = True


# ==================== Search ====================
class SearchResult(BaseModel):
    species: list[SpeciesResponse] = []
    families: list[FamilyResponse] = []
    genera: list[GenusResponse] = []


class SearchTotal(BaseModel):
    species: int = 0
    families: int = 0
    genera: int = 0


class SearchResponse(BaseModel):
    results: SearchResult
    total: SearchTotal


# ==================== SpeciesSubmissions ====================
class SpeciesSubmissionCreate(BaseModel):
    genus_id: int
    chinese_name: str = Field(max_length=100)
    latin_name: str = Field(max_length=150)
    target_species_id: Optional[int] = None
    aliases: Optional[list[str]] = None
    toxicity: Optional[ToxicityLevel] = None
    iucn_status: Optional[IUCNStatus] = None
    discoverer: Optional[str] = Field(None, max_length=100)
    discover_year: Optional[int] = None
    basic_intro: Optional[str] = None
    measurements: Optional[dict] = None
    zoology: Optional[str] = None
    history: Optional[str] = None
    morphology: Optional[str] = None
    distribution: Optional[str] = None
    habitat: Optional[str] = None
    behavior: Optional[str] = None
    reproduction: Optional[str] = None
    conservation: Optional[str] = None
    value: Optional[str] = None
    hazard: Optional[str] = None
    content_format: Optional[str] = "markdown"
    images: Optional[list[SubmissionImageCreate]] = None


class SpeciesSubmissionUpdate(BaseModel):
    genus_id: Optional[int] = None
    chinese_name: Optional[str] = Field(None, max_length=100)
    latin_name: Optional[str] = Field(None, max_length=150)
    target_species_id: Optional[int] = None
    aliases: Optional[list[str]] = None
    toxicity: Optional[ToxicityLevel] = None
    iucn_status: Optional[IUCNStatus] = None
    discoverer: Optional[str] = Field(None, max_length=100)
    discover_year: Optional[int] = None
    basic_intro: Optional[str] = None
    measurements: Optional[dict] = None
    zoology: Optional[str] = None
    history: Optional[str] = None
    morphology: Optional[str] = None
    distribution: Optional[str] = None
    habitat: Optional[str] = None
    behavior: Optional[str] = None
    reproduction: Optional[str] = None
    conservation: Optional[str] = None
    value: Optional[str] = None
    hazard: Optional[str] = None
    content_format: Optional[str] = None
    images: Optional[list[SubmissionImageCreate]] = None


class SpeciesSubmissionReview(BaseModel):
    review_note: Optional[str] = None


class SpeciesSubmissionResponse(BaseModel):
    id: int
    submitter_id: int
    reviewer_id: Optional[int] = None
    chinese_name: str
    latin_name: str
    genus_id: int
    target_species_id: Optional[int] = None
    aliases: Optional[list[str]] = None
    toxicity: Optional[ToxicityLevel] = None
    iucn_status: Optional[IUCNStatus] = None
    discoverer: Optional[str] = None
    discover_year: Optional[int] = None
    basic_intro: Optional[str] = None
    measurements: Optional[dict] = None
    zoology: Optional[str] = None
    history: Optional[str] = None
    morphology: Optional[str] = None
    distribution: Optional[str] = None
    habitat: Optional[str] = None
    behavior: Optional[str] = None
    reproduction: Optional[str] = None
    conservation: Optional[str] = None
    value: Optional[str] = None
    hazard: Optional[str] = None
    content_format: str
    images: list[SubmissionImageResponse] = []
    review_note: Optional[str] = None
    status: SubmissionStatus
    created_species_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
