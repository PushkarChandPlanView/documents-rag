"""Uploader node — saves the synthesized answer as a document via api_gateway."""
import logging
import re as _re
import uuid

from services import upload_client

logger = logging.getLogger(__name__)


def _slugify(text: str, max_len: int = 50) -> str:
    slug = "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")
    slug = _re.sub(r"_+", "_", slug)
    return slug[:max_len]


async def uploader_node(state: dict) -> dict:
    answer   = state.get("answer", "")
    run_id   = state.get("run_id", str(uuid.uuid4()))

    if not answer:
        logger.warning("uploader_node: no answer to upload")
        return {"result_document_id": None}

    # Filename: <agent_name>_<run_id_short>.txt  e.g. "forge_incident_researcher_3fa2c1b0.txt"
    agent_name = state.get("agent_name", "agent")
    name_slug  = _slugify(agent_name)
    filename   = f"{name_slug}_{run_id[:8]}.txt"

    # Upload on behalf of the user who triggered the run so the document
    # appears in their Manage tab and search results (not the service account's).
    user_id = state.get("user_id", "")

    # Get or create a folder named after the agent so all runs are grouped together.
    folder_id = ""
    if agent_name and agent_name != "agent":
        folder_id = await upload_client.get_or_create_folder(
            folder_name=agent_name,
            target_user_email=user_id,
        )
        if folder_id:
            logger.info("uploader_node: uploading into folder '%s' (id=%s)", agent_name, folder_id)
        else:
            logger.warning("uploader_node: could not get/create folder for agent '%s'; uploading to root", agent_name)

    doc_id = await upload_client.upload(
        answer,
        filename,
        source_type="agent",
        target_user_email=user_id,
        folder_id=folder_id,
    )
    logger.info("Agent result uploaded as document_id=%s (owner=%s, folder=%s)", doc_id, user_id, folder_id)
    return {"result_document_id": doc_id}
