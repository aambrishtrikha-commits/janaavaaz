from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.settings import settings

router = APIRouter()


class SubmitBody(BaseModel):
    raw_text: str = Field(min_length=8, max_length=4000)
    source_lang: str = "hi"
    lgd_code: int | None = None
    place_text: str | None = None
    channel: str = "web"
    client_request_id: str | None = None


class DecideBody(BaseModel):
    action: str
    reason: str = ""


def get_corridor():
    from app.main import corridor

    return corridor


@router.get("/health")
async def health() -> dict[str, Any]:
    c = get_corridor()
    return {"ok": True, "mode": settings.app_mode, "packs": c.catalog.health()}


@router.get("/packs")
async def packs() -> dict[str, Any]:
    c = get_corridor()
    return {"packs": c.catalog.health()}


@router.get("/districts")
async def districts(state: str | None = None) -> dict[str, Any]:
    c = get_corridor()
    items = list(c.catalog.districts.values())
    if state:
        items = [d for d in items if d.state_iso2 == state.upper()]
    return {
        "districts": [
            {
                "lgd_code": d.lgd_code,
                "name_en": d.name_en,
                "name_local": d.name_local,
                "state_iso2": d.state_iso2,
                "is_aspirational": d.is_aspirational,
                "lat": d.lat,
                "lng": d.lng,
            }
            for d in items
        ]
    }


@router.post("/tickets")
async def submit(body: SubmitBody) -> dict[str, Any]:
    c = get_corridor()
    lgd = body.lgd_code
    if lgd is None and body.place_text:
        hits = c.catalog.resolve_name(body.place_text)
        lgd = hits[0].lgd_code if hits else None
    rec = c.ledger.submit(
        raw_text=body.raw_text.strip(),
        source_lang=body.source_lang,
        lgd_code=lgd,
        channel=body.channel,
        client_request_id=body.client_request_id,
    )
    rec = await c.hear(rec["ticket_id"])
    rec = await c.brief(rec["ticket_id"])
    return rec


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> dict[str, Any]:
    c = get_corridor()
    rec = c.ledger.tickets.get(ticket_id)
    if not rec:
        raise HTTPException(404, "file not found")
    return rec


@router.get("/track/{pnr}")
async def track(pnr: str) -> dict[str, Any]:
    c = get_corridor()
    for rec in c.ledger.tickets.values():
        if rec["pnr"].lower() == pnr.lower():
            return rec
    raise HTTPException(404, "PNR not found")


@router.get("/board")
async def board() -> dict[str, Any]:
    c = get_corridor()
    files = [t for t in c.ledger.tickets.values() if t["status"] == "briefed"]
    files.sort(key=lambda t: (t.get("score") or {}).get("score", 0), reverse=True)
    return {"files": files[:5], "all": list(c.ledger.tickets.values())}


@router.post("/tickets/{ticket_id}/decide")
async def decide(
    ticket_id: str,
    body: DecideBody,
    x_officer_token: str | None = Header(default=None),
) -> dict[str, Any]:
    if x_officer_token != settings.demo_officer_token:
        raise HTTPException(401, "officer token required")
    c = get_corridor()
    if ticket_id not in c.ledger.tickets:
        raise HTTPException(404, "file not found")
    try:
        return c.decide(ticket_id, body.action, body.reason)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/hotspots")
async def hotspots() -> dict[str, Any]:
    c = get_corridor()
    return {"hotspots": c.hotspots()}


@router.post("/webhooks/whatsapp-sim")
async def wa_sim(payload: dict[str, Any]) -> dict[str, Any]:
    text = str(payload.get("text") or payload.get("body") or "")
    if len(text) < 8:
        raise HTTPException(400, "text too short")
    c = get_corridor()
    rec = c.ledger.submit(
        raw_text=text,
        source_lang=str(payload.get("lang") or "hi"),
        lgd_code=None,
        channel="whatsapp_sim",
        client_request_id=payload.get("id"),
    )
    if payload.get("place"):
        hits = c.catalog.resolve_name(str(payload["place"]))
        if hits:
            rec["lgd_code"] = hits[0].lgd_code
    rec = await c.hear(rec["ticket_id"])
    rec = await c.brief(rec["ticket_id"])
    return rec
