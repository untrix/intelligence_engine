"""Settings page routes: view, save, and test AI provider credentials."""

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import get_templates
from app.models import AppSettings

router = APIRouter(tags=["settings"])


async def get_all_settings(db: AsyncSession) -> dict:
    result = await db.execute(select(AppSettings))
    rows = result.scalars().all()
    return {row.key: row.value for row in rows}


async def save_setting(db: AsyncSession, key: str, value: str):
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value or ""
    else:
        db.add(AppSettings(key=key, value=value or ""))


def _hx_trigger_toast(message: str, toast_type: str = "success", **extra):
    triggers = {"showToast": {"message": message, "type": toast_type}}
    triggers.update(extra)
    return {"HX-Trigger": json.dumps(triggers)}


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    templates = get_templates()
    all_settings = await get_all_settings(db)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "active_page": "settings",
            "settings": all_settings,
        },
    )


@router.post("/settings/save", response_class=HTMLResponse)
async def save_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    openai_api_key: str = Form(""),
    anthropic_api_key: str = Form(""),
    google_api_key: str = Form(""),
    aws_profile: str = Form(""),
    aws_region: str = Form("us-east-1"),
    chrome_cdp_url: str = Form(""),
    default_provider: str = Form("openai"),
    default_model: str = Form(""),
    default_concurrency: str = Form("5"),
    openai_api_key_unchanged: str = Form(""),
    anthropic_api_key_unchanged: str = Form(""),
    google_api_key_unchanged: str = Form(""),
    clear_key: str = Form(""),
):
    all_settings = await get_all_settings(db)

    def _resolve_key(form_val: str, unchanged: str, stored_key: str) -> str:
        if unchanged and not form_val.strip():
            return stored_key or ""
        return form_val

    clearable_keys = {
        "openai": "openai_api_key",
        "anthropic": "anthropic_api_key",
        "google": "google_api_key",
    }
    key_to_clear = clearable_keys.get(clear_key)

    form_data = {
        "openai_api_key": _resolve_key(
            openai_api_key, openai_api_key_unchanged, all_settings.get("openai_api_key", "")
        ),
        "anthropic_api_key": _resolve_key(
            anthropic_api_key,
            anthropic_api_key_unchanged,
            all_settings.get("anthropic_api_key", ""),
        ),
        "google_api_key": _resolve_key(
            google_api_key, google_api_key_unchanged, all_settings.get("google_api_key", "")
        ),
        "aws_profile": aws_profile,
        "aws_region": aws_region,
        "chrome_cdp_url": chrome_cdp_url,
        "default_provider": default_provider,
        "default_model": default_model,
        "default_concurrency": default_concurrency,
    }
    if key_to_clear:
        form_data[key_to_clear] = ""
    for key, value in form_data.items():
        await save_setting(db, key, value)
    await db.commit()
    toast_message = (
        f"{clear_key.capitalize()} API key cleared" if key_to_clear else "Settings saved"
    )
    extra_triggers = {"apiKeyCleared": {"provider": clear_key}} if key_to_clear else {}
    return HTMLResponse(
        content="",
        status_code=200,
        headers=_hx_trigger_toast(toast_message, "success", **extra_triggers),
    )


async def _test_openai(api_key: str) -> tuple[bool, str]:
    if not api_key or not api_key.strip():
        return False, "API key is required"
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key.strip())
        await client.models.list()
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


async def _test_anthropic(api_key: str) -> tuple[bool, str]:
    if not api_key or not api_key.strip():
        return False, "API key is required"
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key.strip())
        await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


async def _test_google(api_key: str) -> tuple[bool, str]:
    if not api_key or not api_key.strip():
        return False, "API key is required"
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel("gemini-1.5-flash")
        await model.generate_content_async("Hi")
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


async def _test_bedrock(profile: str, region: str) -> tuple[bool, str]:
    if not profile or not profile.strip():
        return False, "AWS Profile name is required"
    try:
        import boto3
        from botocore.exceptions import ClientError, ProfileNotFound

        session = boto3.Session(
            profile_name=profile.strip(),
            region_name=region or "us-east-1",
        )
        client = session.client("bedrock")
        client.list_foundation_models()
        return True, "Connection successful"
    except ProfileNotFound:
        return False, f"AWS profile '{profile.strip()}' not found in ~/.aws/credentials"
    except ClientError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


@router.post("/settings/test-provider", response_class=HTMLResponse)
async def test_provider(
    request: Request,
    db: AsyncSession = Depends(get_db),
    provider: str = Form(...),
    openai_api_key: str = Form(""),
    anthropic_api_key: str = Form(""),
    google_api_key: str = Form(""),
    aws_profile: str = Form(""),
    aws_region: str = Form("us-east-1"),
):
    all_settings = await get_all_settings(db)
    openai_key = openai_api_key.strip() or (all_settings.get("openai_api_key") or "")
    anthropic_key = anthropic_api_key.strip() or (all_settings.get("anthropic_api_key") or "")
    google_key = google_api_key.strip() or (all_settings.get("google_api_key") or "")
    profile = aws_profile.strip() or (all_settings.get("aws_profile") or "")
    region = aws_region.strip() or (all_settings.get("aws_region") or "us-east-1")

    success = False
    message = "Unknown provider"
    if provider == "openai":
        success, message = await _test_openai(openai_key)
    elif provider == "anthropic":
        success, message = await _test_anthropic(anthropic_key)
    elif provider == "google":
        success, message = await _test_google(google_key)
    elif provider == "bedrock":
        success, message = await _test_bedrock(profile, region)
    toast_type = "success" if success else "danger"
    return HTMLResponse(
        content="",
        status_code=200,
        headers=_hx_trigger_toast(message, toast_type),
    )
