#!/usr/bin/env python3
"""
Generate IMDF (Indoor Mapping Data Format) GeoJSON files for Microsoft Places.

Produces six .geojson files per building plus a ready-to-upload zip package:
  maps/<building>/building.geojson
  maps/<building>/footprint.geojson
  maps/<building>/level.geojson
  maps/<building>/unit.geojson      ← one unit per desk (carries imdf_unit_id)
  maps/<building>/section.geojson
  maps/<building>/fixture.geojson   ← physical desk shape within each unit
  maps/<building>/imdf_correlated.zip

Also writes maps/imdf_unit_ids.json — a desk-label → IMDF unit UUID mapping used
by update_imdf_ids.py to stamp imdf_unit_id onto desk rows in the database.

Usage:
    cd DeskMate
    uv run python scripts/generate_imdf.py

No project dependencies — stdlib only.
"""

from __future__ import annotations

import datetime
import json
import math
import uuid
import zipfile
from pathlib import Path
from typing import Any

# ── Building definitions ──────────────────────────────────────────────────────
# lat/lng are the centroid of each building.
# width_m × height_m defines the floor footprint size.
# Orientation: "north" edge is the window side.

BUILDINGS: dict[str, dict[str, Any]] = {
    "London": {
        "lat": 51.50474,
        "lng": -0.01963,
        "width_m": 60.0,
        "height_m": 45.0,
        "address": "1 Canada Square, Canary Wharf, London E14 5AB",
        "floors": [
            {"ordinal": 0, "name": "Ground", "short": "G"},
            {"ordinal": 1, "name": "First", "short": "F"},
        ],
        "sections": [
            "Window Bank", "Quiet Zone", "Collaboration Zone",
            "Core Desk Area", "Executive Suite", "Secure Zone",
        ],
    },
    "Leeds": {
        "lat": 53.79591,
        "lng": -1.54709,
        "width_m": 45.0,
        "height_m": 35.0,
        "address": "1 Whitehall Road, Leeds LS1 4HR",
        "floors": [
            {"ordinal": 0, "name": "Ground", "short": "G"},
            {"ordinal": 1, "name": "First", "short": "F"},
        ],
        "sections": ["Window Bank", "Quiet Zone", "Collaboration Zone", "Core Desk Area"],
    },
    "Edinburgh": {
        "lat": 55.94620,
        "lng": -3.20116,
        "width_m": 40.0,
        "height_m": 30.0,
        "address": "1 Festival Square, Edinburgh EH3 9SR",
        "floors": [
            {"ordinal": 0, "name": "Ground", "short": "G"},
            {"ordinal": 1, "name": "First", "short": "F"},
        ],
        "sections": ["Window Bank", "Quiet Zone", "Collaboration Zone", "Core Desk Area"],
    },
}

# ── Section layout ────────────────────────────────────────────────────────────
# (x_frac_min, y_frac_min, x_frac_max, y_frac_max) as fractions of floor
# (0,0) = SW corner (near exit/core), (1,1) = NE corner (window side north)

_LAYOUT_STANDARD: dict[str, tuple[float, float, float, float]] = {
    "Window Bank":        (0.00, 0.72, 1.00, 1.00),
    "Quiet Zone":         (0.00, 0.25, 0.50, 0.72),
    "Collaboration Zone": (0.50, 0.25, 1.00, 0.72),
    "Core Desk Area":     (0.00, 0.00, 1.00, 0.25),
}

_LAYOUT_LONDON: dict[str, tuple[float, float, float, float]] = {
    "Executive Suite":    (0.00, 0.72, 0.28, 1.00),
    "Window Bank":        (0.28, 0.72, 0.72, 1.00),
    "Secure Zone":        (0.72, 0.72, 1.00, 1.00),
    "Quiet Zone":         (0.00, 0.25, 0.50, 0.72),
    "Collaboration Zone": (0.50, 0.25, 1.00, 0.72),
    "Core Desk Area":     (0.00, 0.00, 1.00, 0.25),
}

# Desk count per section — must match seed_demo.py SECTION_DESK_COUNTS
_DESK_COUNTS: dict[str, int] = {
    "Window Bank": 5,
    "Quiet Zone": 5,
    "Collaboration Zone": 5,
    "Core Desk Area": 8,
    "Executive Suite": 4,
    "Secure Zone": 4,
}

# IMDF category and restriction per section
_SECTION_META: dict[str, dict[str, str | None]] = {
    "Window Bank":        {"category": "openspace",    "restriction": None},
    "Quiet Zone":         {"category": "openspace",    "restriction": None},
    "Collaboration Zone": {"category": "openspace",    "restriction": None},
    "Core Desk Area":     {"category": "openspace",    "restriction": None},
    "Executive Suite":    {"category": "room",         "restriction": "restricted"},
    "Secure Zone":        {"category": "room",         "restriction": "restricted"},
}

# ── Microsoft Places real PlaceIds ───────────────────────────────────────────
# IMDF level feature `id` must equal the Places floor PlaceId so the upload
# engine can correlate levels to the existing Place floor records.
# Building IDs are provided for reference; the `-BuildingId` flag on New-Map
# handles the building correlation so the IMDF building `id` can stay as UUID5.

PLACES_IDS: dict[str, dict] = {
    "London": {
        "building": "0c5f0af6-79d9-4f91-8eae-6a792f7bc13d",
        "floors": {
            "Ground": "341797d2-bf21-44c8-adb9-da4b3630ab54",
            "First":  "5a41f85f-a616-42bf-a3ec-ded866a57575",
        },
    },
    "Leeds": {
        "building": "9d0934cb-b8c7-4dee-903a-e4313144ea11",
        "floors": {
            "Ground": "14b03dbb-cfd1-46ac-a1ba-0488c2d5fcbd",
            "First":  "8ff47977-2281-4fcf-a81b-8b60cf053aa9",
        },
    },
    "Edinburgh": {
        "building": "1337eef1-e8f1-4d1e-b206-2d6da477a9a8",
        "floors": {
            "Ground": "b174c278-cd7e-43cf-b72f-95121b2c29fb",
            "First":  "1689f5e3-9244-45fa-b8f1-ca21f8a36a16",
        },
    },
}

# ── Deterministic UUID generation ─────────────────────────────────────────────
# Using UUID5 so IDs are stable across regenerations.

_NS = uuid.UUID("b3a5a7c1-4d2e-4f8a-9c1b-2e3f4a5b6c7d")


def _uid(*parts: str) -> str:
    return str(uuid.uuid5(_NS, "|".join(parts)))


# ── Coordinate helpers ────────────────────────────────────────────────────────

def _scale(lat: float) -> tuple[float, float]:
    """Return (lat_per_m, lng_per_m) degree-per-metre factors at latitude."""
    return (
        1 / 110_574,
        1 / (111_320 * math.cos(math.radians(lat))),
    )


def _rect(
    origin_lat: float, origin_lng: float,
    lat_pm: float, lng_pm: float,
    x0: float, y0: float, x1: float, y1: float,
) -> dict:
    """GeoJSON Polygon from metre offsets relative to SW building origin."""
    sw = [origin_lng + x0 * lng_pm, origin_lat + y0 * lat_pm]
    se = [origin_lng + x1 * lng_pm, origin_lat + y0 * lat_pm]
    ne = [origin_lng + x1 * lng_pm, origin_lat + y1 * lat_pm]
    nw = [origin_lng + x0 * lng_pm, origin_lat + y1 * lat_pm]
    return {"type": "Polygon", "coordinates": [[sw, se, ne, nw, sw]]}


def _centre(polygon: dict) -> list[float]:
    ring = polygon["coordinates"][0][:-1]
    return [
        sum(c[0] for c in ring) / len(ring),
        sum(c[1] for c in ring) / len(ring),
    ]


# ── Feature builders ──────────────────────────────────────────────────────────

def _building_feature(name: str, info: dict) -> tuple[str, dict]:
    bid = PLACES_IDS.get(name, {}).get("building") or _uid("building", name)
    return bid, {
        "type": "Feature",
        "feature_type": "building",
        "id": bid,
        "geometry": {"type": "Point", "coordinates": [info["lng"], info["lat"]]},
        "properties": {
            "name": {"en": f"TheBank — {name}"},
            "alt_name": None,
            "category": "building",
            "restriction": None,
            "accessibility": None,
            "address": {"address": info["address"], "country": "GB"},
        },
    }


def _footprint_feature(name: str, info: dict, building_id: str, origin: tuple) -> dict:
    origin_lat, origin_lng = origin
    lat_pm, lng_pm = _scale(info["lat"])
    poly = _rect(origin_lat, origin_lng, lat_pm, lng_pm, 0, 0, info["width_m"], info["height_m"])
    return {
        "type": "Feature",
        "feature_type": "footprint",
        "id": _uid("footprint", name),
        "geometry": poly,
        "properties": {
            "building_ids": [building_id],
            "name": {"en": f"TheBank — {name} Footprint"},
            "alt_name": None,
            "category": "ground",
        },
    }


def _level_feature(
    bname: str, floor: dict, info: dict, building_id: str, origin: tuple
) -> tuple[str, dict]:
    # Use the real Places floor PlaceId so the upload engine can correlate.
    lid = PLACES_IDS.get(bname, {}).get("floors", {}).get(floor["name"]) or _uid("level", bname, floor["name"])
    origin_lat, origin_lng = origin
    lat_pm, lng_pm = _scale(info["lat"])
    poly = _rect(origin_lat, origin_lng, lat_pm, lng_pm, 0, 0, info["width_m"], info["height_m"])
    return lid, {
        "type": "Feature",
        "feature_type": "level",
        "id": lid,
        "geometry": poly,
        "properties": {
            "building_ids": [building_id],
            "ordinal": floor["ordinal"],
            "name": {"en": f"{floor['name']} Floor"},
            "short_name": {"en": floor["short"]},
            "category": "unspecified",
            "alt_name": None,
            "accessibility": None,
            "restriction": None,
            "address": None,
        },
    }


def _section_unit_fixture_features(
    bname: str,
    floor: dict,
    info: dict,
    level_id: str,
    origin: tuple,
) -> tuple[list[dict], list[dict], list[dict], dict[str, str]]:
    """
    Build section, unit and fixture features for all sections on a floor.

    Returns:
        section_features, unit_features, fixture_features,
        label_to_unit_id  (desk label → IMDF unit UUID)
    """
    origin_lat, origin_lng = origin
    lat_pm, lng_pm = _scale(info["lat"])
    w, h = info["width_m"], info["height_m"]
    layout = _LAYOUT_LONDON if bname == "London" else _LAYOUT_STANDARD

    section_feats: list[dict] = []
    unit_feats: list[dict] = []
    fixture_feats: list[dict] = []
    label_to_uid: dict[str, str] = {}

    for sec_name in info["sections"]:
        if sec_name not in layout:
            continue

        xf0, yf0, xf1, yf1 = layout[sec_name]
        sx0, sy0, sx1, sy1 = xf0 * w, yf0 * h, xf1 * w, yf1 * h
        sec_poly = _rect(origin_lat, origin_lng, lat_pm, lng_pm, sx0, sy0, sx1, sy1)
        sec_meta = _SECTION_META.get(sec_name, {"category": "openspace", "restriction": None})
        sec_id = _uid("section", bname, floor["name"], sec_name)

        section_feats.append({
            "type": "Feature",
            "feature_type": "section",
            "id": sec_id,
            "geometry": sec_poly,
            "properties": {
                "level_id": level_id,
                "name": {"en": sec_name},
                "alt_name": None,
                "category": sec_meta["category"],
                "restriction": sec_meta["restriction"],
                "accessibility": None,
                "address": None,
            },
        })

        # Desk layout: arrange in a grid within the section polygon
        desk_count = _DESK_COUNTS.get(sec_name, 5)
        cols = min(4, desk_count)
        rows = math.ceil(desk_count / cols)
        sec_w = sx1 - sx0
        sec_h = sy1 - sy0
        cell_w = sec_w / (cols + 1)
        cell_h = sec_h / (rows + 1)

        # Desk unit is 2.0m × 1.6m; desk fixture (tabletop) is 1.4m × 0.8m
        unit_hw = min(cell_w * 0.45, 1.0)   # half-width
        unit_hh = min(cell_h * 0.40, 0.8)   # half-height

        # Desk label matches seed_demo.py convention: {B[0]}{F[0]}{S[0]}-NN
        desk_prefix = f"{bname[0]}{floor['name'][0]}{sec_name[0]}-"

        for idx in range(1, desk_count + 1):
            row = (idx - 1) // cols
            col = (idx - 1) % cols
            cx = sx0 + (col + 1) * cell_w    # desk centre x (metres from SW)
            cy = sy0 + (row + 1) * cell_h    # desk centre y

            unit_poly = _rect(
                origin_lat, origin_lng, lat_pm, lng_pm,
                cx - unit_hw, cy - unit_hh,
                cx + unit_hw, cy + unit_hh,
            )
            unit_centre = _centre(unit_poly)
            unit_id = _uid("unit", bname, floor["name"], sec_name, str(idx))
            label = f"{desk_prefix}{idx:02d}"
            label_to_uid[label] = unit_id

            unit_feats.append({
                "type": "Feature",
                "feature_type": "unit",
                "id": unit_id,
                "geometry": unit_poly,
                "properties": {
                    "level_id": level_id,
                    "name": {"en": label},
                    "alt_name": None,
                    "category": "desk",
                    "display_point": {"type": "Point", "coordinates": unit_centre},
                    "restriction": sec_meta["restriction"],
                    "accessibility": None,
                    "labels": [{"value": label, "type": "unit_name"}],
                },
            })

            # Fixture = physical tabletop (smaller than the unit area)
            fix_hw = min(unit_hw * 0.70, 0.70)
            fix_hh = min(unit_hh * 0.55, 0.40)
            fixture_poly = _rect(
                origin_lat, origin_lng, lat_pm, lng_pm,
                cx - fix_hw, cy - fix_hh,
                cx + fix_hw, cy + fix_hh,
            )
            fixture_feats.append({
                "type": "Feature",
                "feature_type": "fixture",
                "id": _uid("fixture", bname, floor["name"], sec_name, str(idx)),
                "geometry": fixture_poly,
                "properties": {
                    "unit_id": unit_id,
                    "level_id": level_id,
                    "name": {"en": label},
                    "alt_name": None,
                    "category": "desk",
                    "labels": [{"value": label, "type": "fixture_name"}],
                    "accessibility": None,
                },
            })

    return section_feats, unit_feats, fixture_feats, label_to_uid


def _write_fc(path: Path, features: list[dict]) -> None:
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=2))
    print(f"    {path.name:30s}  ({len(features):3d} features)")


def _write_manifest(building_dir: Path) -> None:
    manifest = {
        "version": "1.0.0",
        "created": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "language": "en",
        "filename": "manifest.json",
    }
    (building_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"    {'manifest.json':30s}  (IMDF package manifest)")


def _zip_building(building_dir: Path) -> None:
    zip_path = building_dir / "imdf_correlated.zip"
    files = [
        "manifest.json",
        "building.geojson", "footprint.geojson", "level.geojson",
        "unit.geojson", "section.geojson", "fixture.geojson",
    ]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in files:
            fp = building_dir / fname
            if fp.exists():
                zf.write(fp, fname)   # flat structure — no subfolder
    print(f"    {'imdf_correlated.zip':30s}  → ready for Microsoft Places upload")


# ── Main ──────────────────────────────────────────────────────────────────────

def generate_all() -> None:
    maps_root = Path(__file__).parent.parent / "maps"
    maps_root.mkdir(exist_ok=True)

    all_label_uids: dict[str, str] = {}   # "Building/FloorName/Label" → unit_uuid

    for bname, info in BUILDINGS.items():
        print(f"\n◆ {bname}")
        bdir = maps_root / bname.lower()
        bdir.mkdir(exist_ok=True)

        building_id, building_feat = _building_feature(bname, info)
        _write_fc(bdir / "building.geojson", [building_feat])

        lat, lng = info["lat"], info["lng"]
        lat_pm, lng_pm = _scale(lat)
        # SW origin of building footprint
        origin = (
            lat - (info["height_m"] / 2) * lat_pm,
            lng - (info["width_m"] / 2) * lng_pm,
        )

        _write_fc(bdir / "footprint.geojson", [_footprint_feature(bname, info, building_id, origin)])

        level_feats: list[dict] = []
        unit_feats: list[dict] = []
        sec_feats: list[dict] = []
        fix_feats: list[dict] = []

        for floor in info["floors"]:
            level_id, level_feat = _level_feature(bname, floor, info, building_id, origin)
            level_feats.append(level_feat)

            sf, uf, ff, label_map = _section_unit_fixture_features(
                bname, floor, info, level_id, origin
            )
            sec_feats.extend(sf)
            unit_feats.extend(uf)
            fix_feats.extend(ff)

            for label, uid in label_map.items():
                all_label_uids[f"{bname}/{floor['name']}/{label}"] = uid

        _write_fc(bdir / "level.geojson", level_feats)
        _write_fc(bdir / "unit.geojson", unit_feats)
        _write_fc(bdir / "section.geojson", sec_feats)
        _write_fc(bdir / "fixture.geojson", fix_feats)
        _write_manifest(bdir)
        _zip_building(bdir)

    # Write label → unit-ID mapping for update_imdf_ids.py
    id_map = maps_root / "imdf_unit_ids.json"
    id_map.write_text(json.dumps(all_label_uids, indent=2, sort_keys=True))
    print(f"\n✓ ID mapping written → {id_map.relative_to(maps_root.parent)}")
    print(f"  {len(all_label_uids)} desk units mapped")
    print("\nNext steps:")
    print("  1. Upload each maps/<building>/imdf_correlated.zip to Microsoft Places")
    print("     (see maps/README.md for the full upload procedure)")
    print("  2. Run:  uv run python scripts/update_imdf_ids.py")
    print("     to stamp the generated unit IDs onto desk rows in the database")


if __name__ == "__main__":
    generate_all()
