# Microsoft Places — Floor Plan Upload

This directory contains generated IMDF (Indoor Mapping Data Format) packages for
all DeskMate office buildings. Each package is ready to upload to Microsoft Places.

---

## Directory structure

```
maps/
├── london/
│   ├── building.geojson    — building entity
│   ├── footprint.geojson   — building outline polygon
│   ├── level.geojson       — one feature per floor
│   ├── unit.geojson        — one feature per desk (carries imdf_unit_id)
│   ├── section.geojson     — zone groupings (Window Bank, Quiet Zone, etc.)
│   ├── fixture.geojson     — physical desk tabletop shapes
│   └── imdf_correlated.zip — ready-to-upload package
├── leeds/
│   └── ...
├── edinburgh/
│   └── ...
└── imdf_unit_ids.json      — desk label → IMDF unit UUID mapping
```

---

## Step 1: Generate or regenerate the files

Run once (or after any desk layout change):

```powershell
cd DeskMate
uv run python scripts/generate_imdf.py
```

This regenerates all six `.geojson` files and the `.zip` for each building, and
writes `maps/imdf_unit_ids.json`.

---

## Step 2: Find each building's PlaceId in Microsoft Places

```powershell
Get-PlaceV3 -Type Building | Select-Object DisplayName, PlaceId
```

Match the display names to the buildings below:

| DeskMate building | Expected MS Places display name |
|---|---|
| London | TheBank — London |
| Leeds | TheBank — Leeds |
| Edinburgh | TheBank — Edinburgh |

---

## Step 3: Upload each zip package

Run once per building. Replace `<PlaceId>` with the value from Step 2.

```powershell
# London
New-Map -BuildingId <LondonPlaceId> -FilePath "maps\london\imdf_correlated.zip"

# Leeds
New-Map -BuildingId <LeedsPlaceId>  -FilePath "maps\leeds\imdf_correlated.zip"

# Edinburgh
New-Map -BuildingId <EdinburghPlaceId> -FilePath "maps\edinburgh\imdf_correlated.zip"
```

Maps may take up to 1 hour to appear in Microsoft Places.

---

## Step 4: Stamp IMDF unit IDs onto desk records

After upload, run the updater to write `imdf_unit_id` (and `places_building_id`,
`places_floor_id`, `places_section_id`) into the database so the allocation engine
and UI can reference the correct Places objects:

```powershell
# Preview first
uv run python scripts/update_imdf_ids.py --dry-run

# Apply
uv run python scripts/update_imdf_ids.py
```

---

## Section → zone mapping

| IMDF section name | Zone type | Restricted? |
|---|---|---|
| Window Bank | Open plan, north wall | No |
| Quiet Zone | Silent working | No |
| Collaboration Zone | Open plan, social | No |
| Core Desk Area | Standard hot-desking | No |
| Executive Suite | VIP desks *(London only)* | Yes — `is_vip` users only |
| Secure Zone | CSO area *(London only)* | Yes — `restricted_section_ids` required |

---

## Re-uploading after changes

If the floor plan changes (new desks, section rename), re-run Steps 1–4.
The IMDF IDs are deterministic (UUID5), so unchanged desks keep the same
`imdf_unit_id` — only new or renamed features get new IDs.
