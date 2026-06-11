"""HTTP client that uploads result documents to api_gateway."""
import logging

import httpx

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_cached_token: str = ""


async def _get_token() -> str:
    global _cached_token
    if _cached_token:
        return _cached_token
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.api_gateway_url}/api/auth/login",
                json={"email": settings.gw_service_email, "password": settings.gw_service_pass},
            )
            resp.raise_for_status()
            _cached_token = resp.json().get("access_token", "")
            return _cached_token
    except Exception as exc:
        logger.error("upload_client: failed to get token: %s", exc)
        return ""


async def get_or_create_folder(folder_name: str, target_user_email: str = "") -> str:
    """
    Find or create a folder with the given name for the target user.
    Returns the folder UUID as a string, or "" on failure.

    Uses the admin-override ?target_user_email= query param so the folder
    is owned by the real user, not the service account.
    """
    global _cached_token

    params: dict = {}
    if target_user_email:
        params["target_user_email"] = target_user_email

    for retry in (False, True):
        if retry:
            _cached_token = ""
        token = await _get_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # 1. List existing folders for the user
                list_resp = await client.get(
                    f"{settings.api_gateway_url}/api/folders",
                    params=params,
                    headers=headers,
                )
                if list_resp.status_code == 401 and not retry:
                    continue
                list_resp.raise_for_status()
                folders = list_resp.json().get("items", [])
                for folder in folders:
                    if folder.get("name") == folder_name:
                        folder_id = folder.get("id", "")
                        logger.info(
                            "upload_client: found existing folder '%s' id=%s", folder_name, folder_id
                        )
                        return folder_id

                # 2. Folder not found — create it
                create_resp = await client.post(
                    f"{settings.api_gateway_url}/api/folders",
                    params=params,
                    json={"name": folder_name},
                    headers=headers,
                )
                if create_resp.status_code == 401 and not retry:
                    continue
                create_resp.raise_for_status()
                folder_id = create_resp.json().get("id", "")
                logger.info(
                    "upload_client: created folder '%s' id=%s (owner=%s)",
                    folder_name, folder_id, target_user_email or "service-account",
                )
                return folder_id
        except Exception as exc:
            logger.error("upload_client: get_or_create_folder failed: %s", exc)
            return ""
    return ""


async def upload(
    content: str,
    filename: str,
    source_type: str = "agent",
    target_user_email: str = "",
    folder_id: str = "",
) -> str:
    """
    Upload text content as a document. Returns document_id or empty string on failure.

    target_user_email: if provided, the document is created under that user's account
    (api_gateway admin-override). Pass the user_id/email of the agent run's owner so
    the result document appears in their Manage tab and search results.

    folder_id: if provided, place the document inside this folder.
    """
    global _cached_token
    blob = content.encode("utf-8")
    for retry in (False, True):
        if retry:
            _cached_token = ""
        token = await _get_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        form_data: dict = {"source_type": source_type}
        if target_user_email:
            form_data["target_user_email"] = target_user_email
        if folder_id:
            form_data["folder_id"] = folder_id
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{settings.api_gateway_url}/api/documents/upload",
                    files={"file": (filename, blob, "text/plain")},
                    data=form_data,
                    headers=headers,
                )
                if resp.status_code == 401 and not retry:
                    continue
                resp.raise_for_status()
                return resp.json().get("document_id", "")
        except Exception as exc:
            logger.error("upload_client: upload failed: %s", exc)
            return ""
    return ""
