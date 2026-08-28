from sqlalchemy import Column, Integer, String, Text, ForeignKey, VARCHAR, DateTime, func, Enum, Index, text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB,ENUM
from app.services.database import Base

toxicity_level_enum = ENUM(
    '无毒', '微毒', '有毒', '剧毒', '极毒',
    name='toxicity_level',
    create_type=True,
)
iucn_status_enum = ENUM(
    'EX', 'EW', 'CR', 'EN', 'VU', 'NT', 'LC', 'DD', 'NE',
    name='iucn_status',
    create_type=True,
)
user_role_enum = ENUM(
    'admin', 'editor', 'user',
    name='user_role',
    create_type=True,
)
submission_status_enum = ENUM(
    'pending', 'approved', 'rejected',
    name='submission_status',
    create_type=True,
)


class Families(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True)
    chinese_name = Column(VARCHAR(100), nullable=False)
    latin_name = Column(VARCHAR(150), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Genera(Base):
    __tablename__ = "genera"
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('families.id', ondelete="RESTRICT"), nullable=False, index=True)
    chinese_name = Column(String(100), nullable=False)
    latin_name = Column(String(150), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Species(Base):
    __tablename__ = "species"
    id = Column(Integer, primary_key=True)
    genus_id = Column(Integer, ForeignKey('genera.id', ondelete="RESTRICT"), nullable=False)
    chinese_name = Column(String(100), nullable=False)
    latin_name = Column(String(150), nullable=False, unique=True)

    aliases = Column(ARRAY(Text))

    toxicity = Column(toxicity_level_enum)
    iucn_status = Column(iucn_status_enum)

    discoverer = Column(String(100))
    discover_year = Column(Integer)
    basic_intro = Column(Text)

    measurements = Column(JSONB, server_default=text("'{}'::jsonb"))

    view_count = Column(Integer, server_default="0")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_species_genus', genus_id),
        Index('idx_species_aliases', aliases, postgresql_using='gin'),
        Index('idx_species_measurements', measurements, postgresql_using='gin'),
    )
class SpeciesContents(Base):
    __tablename__ = "species_contents"

    id = Column(Integer, primary_key=True)
    species_id = Column(Integer, ForeignKey('species.id', ondelete="CASCADE"), nullable=False, unique=True)

    zoology = Column(Text)
    history = Column(Text)
    morphology = Column(Text)
    distribution = Column(Text)
    habitat = Column(Text)
    behavior = Column(Text)
    reproduction = Column(Text)
    conservation = Column(Text)
    value = Column(Text)
    hazard = Column(Text)

    content_format = Column(String(20), server_default="markdown")
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
class SpeciesImages(Base):
    __tablename__ = "species_images"
    id = Column(Integer, primary_key=True)
    species_id = Column(Integer, ForeignKey('species.id', ondelete="CASCADE"), nullable=False)
    image_url = Column(VARCHAR(500), nullable=False)
    thumbnail_url = Column(VARCHAR(500))
    caption = Column(VARCHAR(255))
    photographer = Column(VARCHAR(100))
    image_type = Column(VARCHAR(50), server_default="overview")
    sort_order = Column(Integer, server_default="0")
    is_cover = Column(Boolean, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        Index('idx_images_species', species_id),
        Index('idx_images_cover', species_id, is_cover, postgresql_where=(is_cover == True)),
    )


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(VARCHAR(50), nullable=False, unique=True)
    email = Column(VARCHAR(150), nullable=False, unique=True)
    hashed_password = Column(VARCHAR(255), nullable=False)
    avatar_url = Column(VARCHAR(500))
    role = Column(user_role_enum, nullable=False, server_default="user")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_users_email', email),
        Index('idx_users_username', username),
    )


class UserFavorites(Base):
    __tablename__ = "user_favorites"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    species_id = Column(Integer, ForeignKey('species.id', ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_favorites_user', user_id),
        Index('idx_favorites_species', species_id),
        UniqueConstraint('user_id', 'species_id', name='uq_user_species'),
    )


class SpeciesSubmissions(Base):
    __tablename__ = "species_submissions"
    id = Column(Integer, primary_key=True)
    submitter_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey('users.id', ondelete="SET NULL"))

    chinese_name = Column(String(100), nullable=False)
    latin_name = Column(String(150), nullable=False)
    genus_id = Column(Integer, ForeignKey('genera.id', ondelete="RESTRICT"), nullable=False)

    aliases = Column(ARRAY(Text))
    toxicity = Column(toxicity_level_enum)
    iucn_status = Column(iucn_status_enum)
    discoverer = Column(String(100))
    discover_year = Column(Integer)
    basic_intro = Column(Text)
    measurements = Column(JSONB, server_default=text("'{}'::jsonb"))

    zoology = Column(Text)
    history = Column(Text)
    morphology = Column(Text)
    distribution = Column(Text)
    habitat = Column(Text)
    behavior = Column(Text)
    reproduction = Column(Text)
    conservation = Column(Text)
    value = Column(Text)
    hazard = Column(Text)
    content_format = Column(String(20), server_default="markdown")
    images = Column(JSONB, server_default=text("'[]'::jsonb"))

    target_species_id = Column(Integer, ForeignKey('species.id', ondelete="SET NULL"))
    review_note = Column(Text)
    status = Column(submission_status_enum, nullable=False, server_default="pending")
    created_species_id = Column(Integer, ForeignKey('species.id', ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index('idx_submissions_submitter', submitter_id),
        Index('idx_submissions_status', status),
        Index('idx_submissions_genus', genus_id),
    )
