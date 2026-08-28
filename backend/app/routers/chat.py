from pydantic import BaseModel
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.services.llm_service import llm_query

router = APIRouter(tags=["聊天"])


class ChatRequest(BaseModel):
    query: str


@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        llm_query(req.query),
        media_type="text/event-stream",
    )