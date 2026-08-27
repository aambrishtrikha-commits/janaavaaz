"""Gemini is a munshi with tools — not a chat box."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.settings import settings
from app.domain.pack import PackCatalog


def load_laws() -> str:
    parts = []
    for name in ("munshi.md", "forbidden.md", "schemes.md"):
        p = settings.context_root / name
        if p.exists():
            parts.append(p.read_text())
    return "\n\n".join(parts)


def pack_tool_payload(catalog: PackCatalog, lgd: int | None, sector: str | None) -> dict[str, Any]:
    if lgd is None:
        return {"district": None, "indicators": []}
    dist = catalog.districts.get(lgd)
    inds = catalog.indicators_for(lgd, sector)
    return {
        "district": None
        if not dist
        else {
            "lgd_code": dist.lgd_code,
            "name_en": dist.name_en,
            "state_iso2": dist.state_iso2,
            "is_aspirational": dist.is_aspirational,
        },
        "indicators": [
            {
                "sector": i.sector,
                "code": i.indicator_code,
                "name": i.indicator_name,
                "value": i.value_num,
                "unit": i.unit,
                "direction": i.direction,
                "vintage": i.vintage,
                "source_url": i.source_url,
                "license": i.license,
            }
            for i in inds
        ],
    }


async def run_structured(
    *,
    system: str,
    user: str,
    schema: dict,
    fixture_path: Path | None,
) -> dict[str, Any]:
    if settings.use_fixtures or not settings.gemini_api_key:
        if fixture_path and fixture_path.exists():
            return json.loads(fixture_path.read_text())
        raise RuntimeError("No fixture and no GEMINI_API_KEY")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    text = response.text or "{}"
    return json.loads(text)
