from pathlib import Path

from app.domain.pack import PackCatalog


def test_mh_nandurbar_join():
    root = Path(__file__).resolve().parents[2] / "data" / "packs"
    cat = PackCatalog(root)
    hits = cat.resolve_name("Nandurbar")
    assert hits
    assert hits[0].is_aspirational
    water = cat.indicators_for(hits[0].lgd_code, "water")
    assert water
    assert water[0].source_url.startswith("http")
