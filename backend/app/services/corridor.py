from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.core.settings import settings
from app.core.state import TicketStatus, can_transition
from app.domain.pack import PackCatalog
from app.domain.score import priority_score
from app.providers.gemini_tools import load_laws, pack_tool_payload, run_structured

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(IST)


def pnr(state: str, n: int) -> str:
    return f"JA-{state}-{n:04d}"


class MemoryLedger:
    def __init__(self, catalog: PackCatalog) -> None:
        self.catalog = catalog
        self.tickets: dict[str, dict[str, Any]] = {}
        self.seq = 0
        self.idem: dict[str, str] = {}

    def submit(
        self,
        *,
        raw_text: str,
        source_lang: str,
        lgd_code: int | None,
        channel: str,
        client_request_id: str | None,
        photo_name: str | None = None,
        voice_name: str | None = None,
    ) -> dict[str, Any]:
        if client_request_id and client_request_id in self.idem:
            return self.tickets[self.idem[client_request_id]]
        self.seq += 1
        state = "XX"
        if lgd_code and lgd_code in self.catalog.districts:
            state = self.catalog.districts[lgd_code].state_iso2
        tid = str(uuid.uuid4())
        rec = {
            "ticket_id": tid,
            "pnr": pnr(state, self.seq),
            "status": TicketStatus.RECEIVED.value,
            "raw_text": raw_text,
            "source_lang": source_lang,
            "lgd_code": lgd_code,
            "channel": channel,
            "photo_name": photo_name,
            "voice_name": voice_name,
            "hearing": None,
            "brief": None,
            "score": None,
            "echo": [],
            "created_at": now_ist().isoformat(),
            "timeline": [{"at": now_ist().isoformat(), "status": "received", "note": "File opened"}],
        }
        self.tickets[tid] = rec
        if client_request_id:
            self.idem[client_request_id] = tid
        return rec

    def _move(self, rec: dict, nxt: TicketStatus, note: str) -> None:
        cur = TicketStatus(rec["status"])
        if not can_transition(cur, nxt):
            raise ValueError(f"illegal transition {cur} -> {nxt}")
        rec["status"] = nxt.value
        rec["timeline"].append({"at": now_ist().isoformat(), "status": nxt.value, "note": note})


class Corridor:
    def __init__(self, catalog: PackCatalog, ledger: MemoryLedger) -> None:
        self.catalog = catalog
        self.ledger = ledger

    async def hear(self, ticket_id: str) -> dict[str, Any]:
        rec = self.ledger.tickets[ticket_id]
        fixture = settings.fixture_root / "hearing" / "default.json"
        user = f"Citizen text:\n{rec['raw_text']}\nDeclared language: {rec['source_lang']}\nDeclared LGD: {rec['lgd_code']}\n"
        hearing = await run_structured(
            system=load_laws() + "\nReturn only the Hearing object.",
            user=user,
            schema={},
            fixture_path=fixture,
        )
        if rec["lgd_code"] is None and hearing.get("place_guess"):
            hits = self.catalog.resolve_name(str(hearing["place_guess"]))
            if hits:
                rec["lgd_code"] = hits[0].lgd_code
                rec["pnr"] = pnr(hits[0].state_iso2, int(rec["pnr"].split("-")[-1]))
        rec["hearing"] = hearing
        rec["echo"] = self._echo(rec)
        self.ledger._move(rec, TicketStatus.HEARD, "Gemini Hearing filed")
        return rec

    async def brief(self, ticket_id: str) -> dict[str, Any]:
        rec = self.ledger.tickets[ticket_id]
        lgd = rec.get("lgd_code")
        sector = (rec.get("hearing") or {}).get("sector") or "water"
        tools = pack_tool_payload(self.catalog, lgd, sector)
        fixture = settings.fixture_root / "brief" / f"{sector}-{lgd}.json"
        if not fixture.exists():
            fixture = settings.fixture_root / "brief" / "water-472.json"
        brief = await run_structured(
            system=load_laws() + "\nReturn only the Brief object.",
            user=f"Hearing:\n{rec.get('hearing')}\nTool payload:\n{tools}\n",
            schema={},
            fixture_path=fixture,
        )
        if not tools["indicators"]:
            brief["insufficient_official_data"] = True
            brief["citations"] = []
        rec["brief"] = brief
        rec["score"] = self._score(rec, sector)
        rec["glass"] = {
            "model": settings.gemini_model if settings.gemini_api_key and not settings.use_fixtures else "fixture-replay",
            "region": settings.gcp_region,
            "provider": "gemini" if settings.gemini_api_key and not settings.use_fixtures else "fixture",
            "tools_called": ["get_unit_indicators", "get_district"],
            "allowed_inputs": ["raw_text", "lgd_code", "pack_indicators"],
            "policy_version": "munshi-2026.1",
        }
        self.ledger._move(rec, TicketStatus.BRIEFED, "Gemini Brief + Dissent on file")
        return rec

    def decide(self, ticket_id: str, action: str, reason: str = "") -> dict[str, Any]:
        rec = self.ledger.tickets[ticket_id]
        if action == "publish":
            brief = rec.get("brief") or {}
            if not brief.get("dissent"):
                raise ValueError("dissent required")
            if not brief.get("insufficient_official_data") and not brief.get("citations"):
                raise ValueError("citations required unless insufficient data")
            self.ledger._move(rec, TicketStatus.PUBLISHED, reason or "Officer published")
        elif action == "send_back":
            self.ledger._move(rec, TicketStatus.SENT_BACK, reason or "Sent back")
        elif action == "merge":
            self.ledger._move(rec, TicketStatus.MERGED, reason or "Merged")
        else:
            raise ValueError("unknown action")
        return rec

    def _echo(self, rec: dict) -> list[dict]:
        lgd = rec.get("lgd_code")
        out = []
        for other in self.ledger.tickets.values():
            if other["ticket_id"] == rec["ticket_id"]:
                continue
            if other.get("lgd_code") == lgd and other.get("raw_text"):
                out.append({"pnr": other["pnr"], "line": other["raw_text"][:140], "lang": other.get("source_lang")})
        return out[:3]

    def _score(self, rec: dict, sector: str) -> dict:
        lgd = rec.get("lgd_code")
        dist = self.catalog.districts.get(lgd) if lgd else None
        inds = self.catalog.indicators_for(lgd, sector) if lgd else []
        val = inds[0].value_num if inds else None
        direction = inds[0].direction if inds else None
        peers = [t for t in self.ledger.tickets.values() if t.get("lgd_code") == lgd]
        return priority_score(
            ticket_count=max(1, len(peers)),
            unique_voices=max(1, len({t.get("raw_text", "")[:40] for t in peers})),
            indicator_value=val,
            direction=direction,
            is_aspirational=bool(dist and dist.is_aspirational),
            already_funded_hint=0.2 if val and val >= 80 else 0.05,
        )

    def hotspots(self) -> list[dict]:
        buckets: dict[tuple[int, str], list] = {}
        for t in self.ledger.tickets.values():
            if not t.get("lgd_code"):
                continue
            sector = (t.get("hearing") or {}).get("sector") or "other"
            buckets.setdefault((t["lgd_code"], sector), []).append(t)
        rows = []
        for (lgd, sector), items in buckets.items():
            dist = self.catalog.districts.get(lgd)
            if not dist:
                continue
            k_ok = len(items) >= settings.k_anon_min or settings.app_mode == "demo"
            rows.append({
                "lgd_code": lgd,
                "name_en": dist.name_en,
                "state_iso2": dist.state_iso2,
                "is_aspirational": dist.is_aspirational,
                "sector": sector,
                "ticket_count": len(items) if k_ok else None,
                "published": sum(1 for i in items if i["status"] == TicketStatus.PUBLISHED.value),
                "lat": dist.lat,
                "lng": dist.lng,
                "k_anon_ok": k_ok,
            })
        return rows
