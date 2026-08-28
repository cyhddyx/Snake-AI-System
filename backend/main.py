import uvicorn
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.services.database import engine, Base
from app.routers import auth, chat, families, genera, search, species, species_contents, species_images, species_submissions, users, user_favorites


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                ALTER TABLE species_submissions
                ADD COLUMN IF NOT EXISTS images jsonb DEFAULT '[]'::jsonb
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE species_submissions
                ADD COLUMN IF NOT EXISTS target_species_id INTEGER REFERENCES species(id) ON DELETE SET NULL
                """
            )
        )
    yield


app = FastAPI(title="蛇类百科AI助手 API", version="1.0.0", lifespan=lifespan)

default_cors_origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
]
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(default_cors_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "蛇类百科AI助手 API", "version": "1.0.0"}


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(families.router)
app.include_router(genera.router)
app.include_router(search.router)
app.include_router(species.router)
app.include_router(species_contents.router)
app.include_router(species_images.router)
app.include_router(species_submissions.router)
app.include_router(users.router)
app.include_router(user_favorites.router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
