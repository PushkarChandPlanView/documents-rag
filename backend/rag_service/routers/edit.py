import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import llm_client
from utils.prompt_templates import EDIT_PROMPT, XLSX_EDIT_PROMPT

logger = logging.getLogger(__name__)
router = APIRouter(tags=["edit"])

MAX_CONTENT_CHARS = 80_000

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class EditRequest(BaseModel):
    document_text: str
    instruction: str
    mime_type: Optional[str] = None


class EditResponse(BaseModel):
    proposed_text: str


@router.post("/edit", response_model=EditResponse)
async def edit_document(request: EditRequest) -> EditResponse:
    text = request.document_text[:MAX_CONTENT_CHARS]
    mime = (request.mime_type or "").lower().strip()

    if mime == MIME_XLSX:
        prompt = XLSX_EDIT_PROMPT.format(document_text=text, instruction=request.instruction)
    else:
        prompt = EDIT_PROMPT.format(document_text=text, instruction=request.instruction)

    try:
        proposed_text = await llm_client.generate(prompt)
    except Exception as exc:
        logger.error("LLM edit generation failed: %s", exc)
        raise HTTPException(status_code=502, detail="LLM generation failed") from exc

    return EditResponse(proposed_text=proposed_text)
