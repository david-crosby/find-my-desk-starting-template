#!/usr/bin/env python3
"""
Stamp IMDF unit UUIDs onto desk rows in the database.

Run this after generate_imdf.py has been executed and the IMDF packages have
been uploaded to Microsoft Places. The script reads maps/imdf_unit_ids.json
and updates Desk.imdf_unit_id for every matched desk.

Also updates Building.places_building_id, Floor.places_floor_id, and
Section.places_section_id using the same deterministic UUID scheme so the
database stays aligned with the IMDF file IDs.

Usage:
    cd DeskMate
    uv run python scripts/update_imdf_ids.py [--dry-run]
"""

import sys
import json
import uuid
import argparse
from pathlib import Path

_ROOT = Path(__file__).parent.parent
for _pkg in ("core", "backend", "agent"):
    _src = _ROOT / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from places_core.db import SessionLocal
from places_core.models import Building, Desk, Floor, Section

# Must match the namespace in generate_imdf.py
_NS = uuid.UUID("b3a5a7c1-4d2e-4f8a-9c1b-2e3f4a5b6c7d")


def _uid(*parts: str) -> str:
    return str(uuid.uuid5(_NS, "|".join(parts)))


def main(dry_run: bool = False) -> None:
    id_map_path = _ROOT / "maps" / "imdf_unit_ids.json"
    if not id_map_path.exists():
        print(f"ERROR: {id_map_path} not found.")
        print("Run 'uv run python scripts/generate_imdf.py' first.")
        sys.exit(1)

    label_to_uid: dict[str, str] = json.loads(id_map_path.read_text())

    # Build index: (building_name, floor_name, desk_label) → unit_id
    index: dict[tuple[str, str, str], str] = {}
    for key, uid in label_to_uid.items():
        parts = key.split("/", 2)
        if len(parts) == 3:
            index[(parts[0], parts[1], parts[2])] = uid

    db = SessionLocal()
    try:
        buildings = {b.name: b for b in db.query(Building).all()}
        floors = db.query(Floor).all()
        sections = db.query(Section).all()
        desks = db.query(Desk).all()

        updated_buildings = updated_floors = updated_sections = updated_desks = 0

        # ── Buildings ────────────────────────────────────────────────────────
        for bname, bldg in buildings.items():
            new_id = _uid("building", bname)
            if bldg.places_building_id != new_id:
                if not dry_run:
                    bldg.places_building_id = new_id
                updated_buildings += 1

        # ── Floors ───────────────────────────────────────────────────────────
        floor_name_map = {0: "Ground", 1: "First"}
        for fl in floors:
            bldg = buildings.get(fl.building.name) if fl.building_id else None
            if bldg is None:
                continue
            floor_name = floor_name_map.get(fl.number, fl.name or str(fl.number))
            new_id = _uid("level", bldg.name, floor_name)
            if fl.places_floor_id != new_id:
                if not dry_run:
                    fl.places_floor_id = new_id
                updated_floors += 1

        # ── Sections ─────────────────────────────────────────────────────────
        for sec in sections:
            floor = next((f for f in floors if f.id == sec.floor_id), None)
            if floor is None or floor.building_id is None:
                continue
            bldg_name = next(
                (b.name for b in buildings.values() if b.id == floor.building_id), None
            )
            if not bldg_name:
                continue
            floor_name = floor_name_map.get(floor.number, floor.name or str(floor.number))
            new_id = _uid("section", bldg_name, floor_name, sec.name)
            if sec.places_section_id != new_id:
                if not dry_run:
                    sec.places_section_id = new_id
                updated_sections += 1

        # ── Desks ────────────────────────────────────────────────────────────
        section_map = {s.id: s for s in sections}
        floor_map = {f.id: f for f in floors}
        building_map = {b.id: b for b in buildings.values()}

        for desk in desks:
            sec = section_map.get(desk.section_id)
            if sec is None:
                continue
            fl = floor_map.get(sec.floor_id)
            if fl is None:
                continue
            bldg = building_map.get(fl.building_id)
            if bldg is None:
                continue

            floor_name = floor_name_map.get(fl.number, fl.name or str(fl.number))
            key = (bldg.name, floor_name, desk.label)
            unit_id = index.get(key)

            if unit_id and desk.imdf_unit_id != unit_id:
                if not dry_run:
                    desk.imdf_unit_id = unit_id
                updated_desks += 1

        if not dry_run:
            db.commit()
            print("Database updated:")
        else:
            print("Dry run — no changes written:")

        print(f"  Buildings  : {updated_buildings} updated")
        print(f"  Floors     : {updated_floors} updated")
        print(f"  Sections   : {updated_sections} updated")
        print(f"  Desks      : {updated_desks} updated")

        if dry_run:
            print("\nRerun without --dry-run to apply.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stamp IMDF unit IDs onto database rows.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
