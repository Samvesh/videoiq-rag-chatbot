import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from services.rag_service import answer_question_generator

router = APIRouter()


class ChatRequest(BaseModel):
    question: Optional[str] = None
    message: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/chat", summary="Stream an LLM answer over ingested video data")
async def chat(request: ChatRequest):
    query = request.question or request.message
    if not query:
        raise HTTPException(status_code=400, detail="Either 'question' or 'message' must be provided.")

    try:
        async def token_generator():
            for payload in answer_question_generator(
                query=query,
                session_id=request.session_id or "default"
            ):
                # Server-Sent Events format with JSON stringified payload
                yield f"data: {json.dumps(payload)}\n\n"
            # Final completion marker in valid JSON
            yield f"data: {json.dumps({'token': ''})}\n\n"

        return StreamingResponse(
            token_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

