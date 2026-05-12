#!/usr/bin/env python3
"""
Fill the PlaceId column in each building's mapfeatures.csv.

Import-MapCorrelations (step 1) dumps all IMDF features to a CSV with an empty
PlaceId column. This script fills that column for Building and Level rows by
copying FeatureId → PlaceId (the IMDF generator already uses the real Places
PlaceIds as those feature IDs).

Run AFTER the first Import-MapCorrelations pass and BEFORE the second:

    cd DeskMate
    # Generate CSVs for all buildings first:
    #   Import-MapCorrelations -MapFilePath maps/<b>/imdf_correlated.zip
    # Then:
    python3 scripts/fill_map_correlations.py
"""

import csv
from pathlib import Path

_MAPS = Path(__file__).parent.parent / "maps"
_BUILDINGS = ["london", "leeds", "edinburgh"]


def fill(csv_path: Path) -> int:
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            if row["FeatureType"] in ("Building", "Level") and not row["PlaceId"]:
                row["PlaceId"] = row["FeatureId"]
            rows.append(row)

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return sum(
        1 for r in rows
        if r["FeatureType"] in ("Building", "Level") and r["PlaceId"]
    )


def main() -> None:
    for bname in _BUILDINGS:
        csv_path = _MAPS / bname / "mapfeatures.csv"
        if not csv_path.exists():
            print(f"  {bname:12s}  SKIP — mapfeatures.csv not found")
            print(f"              Run: Import-MapCorrelations -MapFilePath maps/{bname}/imdf_correlated.zip")
            continue
        n = fill(csv_path)
        print(f"  {bname:12s}  {n} Building/Level rows have PlaceId set")


if __name__ == "__main__":
    main()
