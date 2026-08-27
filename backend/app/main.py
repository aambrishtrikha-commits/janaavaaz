from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.settings import settings
from app.domain.pack import PackCatalog
from app.services.corridor import Corridor, MemoryLedger

catalog = PackCatalog(settings.pack_root)
ledger = MemoryLedger(catalog)
corridor = Corridor(catalog, ledger)


def seed_demo() -> None:
    samples = [
        ("Nandurbar tap dry for three months", "hi", 472),
        ("Handpump dry since March in Nandurbar village", "en", 472),
        ("Nandurbar road to haat is broken after rain", "en", 472),
        ("No drinking water in Dhubri ward", "en", 283),
        ("Dhubri drinking water missing", "as", 283),
    ]
    for text, lang, lgd in samples:
        if any(t["raw_text"] == text for t in ledger.tickets.values()):
            continue
        ledger.submit(
            raw_text=text,
            source_lang=lang,
            lgd_code=lgd,
            channel="seed",
            client_request_id=f"seed-{lgd}-{lang}-{text[:12]}",
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.media_root.mkdir(parents=True, exist_ok=True)
    catalog.load()
    seed_demo()
    heard = [t for t in ledger.tickets.values() if t["status"] == "received"]
    for rec in heard[:4]:
        await corridor.hear(rec["ticket_id"])
        await corridor.brief(rec["ticket_id"])
    yield


app = FastAPI(
    title="JanAvaaz Priority Engine",
    version="0.2.0",
    description="Citizen voice to Gemini file to officer stamp.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

_frontend = settings.repo_root / "frontend"
if _frontend.exists():
    app.mount("/static", StaticFiles(directory=_frontend), name="static")

    @app.get("/")
    async def index():
        from fastapi.responses import FileResponse

        return FileResponse(_frontend / "index.html")


@app.get("/api/policy")
async def policy() -> dict[str, str]:
    return {
        "banner": "Sandbox: synthetic citizen text + cited public statistics. Not a government service.",
        "gemini": "Sandbox audio/text may be sent to Gemini. Do not upload real PII.",
    }
