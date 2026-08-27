from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import csv
import yaml


@dataclass(frozen=True, slots=True)
class District:
    lgd_code: int
    name_en: str
    name_local: str
    is_aspirational: bool
    state_iso2: str
    lat: float | None
    lng: float | None


@dataclass(frozen=True, slots=True)
class Indicator:
    lgd_code: int
    sector: str
    indicator_code: str
    indicator_name: str
    value_num: float
    unit: str
    direction: str
    vintage: str
    source_url: str
    license: str


@dataclass(frozen=True, slots=True)
class PackMeta:
    pack_id: str
    state_iso2: str
    state_name: str
    status: str
    languages_default: list[str]
    sectors: list[str]


class PackCatalog:
    """Hot-reloadable India packs. Second state = another folder."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.meta: dict[str, PackMeta] = {}
        self.districts: dict[int, District] = {}
        self.by_name: dict[str, list[int]] = {}
        self.indicators: list[Indicator] = []
        self.load()

    def load(self) -> None:
        self.meta.clear()
        self.districts.clear()
        self.by_name.clear()
        self.indicators.clear()
        india = self.root / "in"
        if not india.exists():
            return
        for folder in india.iterdir():
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            man_path = folder / "manifest.yaml"
            if not man_path.exists():
                continue
            raw = yaml.safe_load(man_path.read_text()) or {}
            meta = PackMeta(
                pack_id=str(raw.get("pack_id", folder.name)),
                state_iso2=str(raw.get("state_iso2", folder.name)).upper(),
                state_name=str(raw.get("state_name", folder.name)),
                status=str(raw.get("status", "awaiting")),
                languages_default=list(raw.get("languages_default") or ["en"]),
                sectors=list(raw.get("sectors") or ["water"]),
            )
            self.meta[meta.state_iso2] = meta
            dist_file = folder / "lgd_districts.csv"
            if dist_file.exists():
                with dist_file.open() as fh:
                    for row in csv.DictReader(fh):
                        code = int(row["lgd_code"])
                        dist = District(
                            lgd_code=code,
                            name_en=row["name_en"].strip(),
                            name_local=row.get("name_local", "").strip(),
                            is_aspirational=str(row.get("is_aspirational", "")).lower() == "true",
                            state_iso2=meta.state_iso2,
                            lat=_f(row.get("centroid_lat")),
                            lng=_f(row.get("centroid_lng")),
                        )
                        self.districts[code] = dist
                        self.by_name.setdefault(dist.name_en.lower(), []).append(code)
                        if dist.name_local:
                            self.by_name.setdefault(dist.name_local.lower(), []).append(code)
            ind_file = folder / "indicators.csv"
            if ind_file.exists():
                with ind_file.open() as fh:
                    for row in csv.DictReader(fh):
                        self.indicators.append(
                            Indicator(
                                lgd_code=int(row["lgd_code"]),
                                sector=row["sector"].strip(),
                                indicator_code=row["indicator_code"].strip(),
                                indicator_name=row["indicator_name"].strip(),
                                value_num=float(row["value_num"]),
                                unit=row["unit"].strip(),
                                direction=row["direction"].strip(),
                                vintage=row["vintage"].strip(),
                                source_url=row["source_url"].strip(),
                                license=row["license"].strip(),
                            )
                        )

    def resolve_name(self, q: str) -> list[District]:
        needle = q.strip().lower()
        if not needle:
            return []
        hits: list[District] = []
        for name, codes in self.by_name.items():
            if needle in name:
                for c in codes:
                    hits.append(self.districts[c])
        seen: set[int] = set()
        out: list[District] = []
        for d in hits:
            if d.lgd_code not in seen:
                seen.add(d.lgd_code)
                out.append(d)
        return out[:8]

    def indicators_for(self, lgd: int, sector: str | None = None) -> list[Indicator]:
        rows = [i for i in self.indicators if i.lgd_code == lgd]
        if sector:
            rows = [i for i in rows if i.sector == sector]
        return rows

    def health(self) -> list[dict]:
        rows = []
        for iso, meta in sorted(self.meta.items()):
            dist = [d for d in self.districts.values() if d.state_iso2 == iso]
            inds = [i for i in self.indicators if i.lgd_code in {d.lgd_code for d in dist}]
            rows.append(
                {
                    "state_iso2": iso,
                    "state_name": meta.state_name,
                    "status": meta.status,
                    "districts": len(dist),
                    "indicator_rows": len(inds),
                    "sectors": meta.sectors,
                }
            )
        return rows


def _f(v: str | None) -> float | None:
    if v is None or v == "":
        return None
    return float(v)
