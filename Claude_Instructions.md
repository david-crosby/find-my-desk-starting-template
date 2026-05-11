# INSTRUCTIONS.md
## Project Context for Claude and Team

Read this file before writing any code or making any decisions. It is the single source of truth for what this project is, how it is structured, and how all work must be done.

---

## Project Name

**DeskMate** — an AI-powered desk and room booking system, built as a Condeco replacement POC for a hackathon. It is built on top of Microsoft Places.

---

## What This Project Does

DeskMate allows users to book desks and rooms using natural language via a conversational AI agent. Bookings are queued and processed each night by an allocation engine that assigns the best available desk based on the user's preferences, working patterns, team location, and environmental factors.

Microsoft Places provides automatic check-in via network or hardware presence detection. If a user does not show up, their desk is released for same-day re-use. A feedback loop after each visit updates user preferences for future allocations. A management intelligence dashboard shows utilisation, no-shows, and demand patterns.

---

## Technology Stack

- **Language:** Python 3.12
- **Package manager:** uv (not pip)
- **AI agent:** Claude API — model `claude-sonnet-4-20250514`
- **API framework:** FastAPI
- **Database:** SQLite via SQLAlchemy (ORM)
- **Dashboard:** Streamlit
- **Scheduling:** APScheduler
- **Workplace integration:** Microsoft Places API
- **Config:** python-dotenv

---

## Database Schema Overview

### users
Stores user identity and preferences.
```
id, name, email, ms_user_id, preferred_desk_type, preferred_zone,
preferred_floor, preferred_building_id, preferred_equipment (JSON),
working_days (JSON), anchor_days (JSON), noise_preference,
lighting_preference, created_at, updated_at
```

### buildings
```
id, name, address, city, ms_place_id
```

### desks
```
id, building_id, floor, zone, desk_number, desk_type,
equipment (JSON), noise_level, natural_light, standing_option,
is_active
```

### rooms
```
id, building_id, floor, name, capacity, equipment (JSON),
ms_place_id, is_active
```

### bookings
```
id, user_id, date, desk_id (nullable), room_id (nullable),
status (queued | allocated | cancelled | no_show | completed),
requested_at, notes
```

### allocations
```
id, booking_id, desk_id (nullable), room_id (nullable),
score, allocated_at, allocation_run_date
```

### checkins
```
id, user_id, desk_id (nullable), room_id (nullable),
detected_at, detection_method (network | hardware | manual),
ms_event_id
```

### feedback
```
id, booking_id, user_id, rating (1-5), comments,
desk_comfort, noise_rating, equipment_rating, submitted_at
```

---

## Agent Behaviour

The agent is the entry point for all user interactions. It must:

1. Parse natural language booking requests into structured intents
2. Ask clarifying questions when the request is ambiguous
3. Write the booking to the `bookings` table with status `queued`
4. Confirm to the user that the request is queued and will be confirmed the following morning
5. Handle cancellations, amendments, and preference updates
6. After a visit is completed, follow up to request feedback
7. Use feedback to update the user's preference profile in the `users` table

The agent uses the Anthropic API with tool use (function calling) to interact with the database. It does not have direct SQL access — all writes go through defined tool functions.

---

## Nightly Allocation Engine

Runs at 23:00 each night (APScheduler). For each booking with status `queued` for the following day:

1. Retrieve all available desks or rooms for that date
2. Score each option against the user's preferences using a weighted scoring function
3. Assign the highest scoring available option
4. Write the result to `allocations` and update the booking status to `allocated`
5. Trigger the notification service for each confirmed allocation
6. Any booking that cannot be fulfilled is marked `waitlisted` and the user notified

Scoring weights (configurable in environment):
- Building match: 30
- Floor match: 20
- Zone match: 20
- Desk type match: 15
- Equipment match: 10
- Noise preference match: 5

---

## Microsoft Places Integration

For the POC this integration is partially mocked. The integration module must:

- Provide a function to register a user presence event (real or mock)
- On a presence event, find the matching desk and update the `checkins` table
- Expose an endpoint `POST /webhook/places` to receive MS Places events
- Run a check at a configurable cut-off time (default 10:00) to mark no-shows and release desks

---

## MI Dashboard

Built in Streamlit. Must show:

- Today's occupancy by building and floor (live)
- No-show rate for the last 30 days
- Desk utilisation heatmap by day of week
- Top 10 most and least used desks
- Feedback score trends

---

## Coding Standards

All code must follow these rules without exception:

- Use British English in all comments, docstrings, print output, and log messages
- Comments explain why, not how — only add a how comment where the logic is genuinely non-obvious
- No emojis anywhere in code, comments, or output
- Use standard single hyphens in CLI flags and options
- Use `uv` for all package management — never pip
- Keep functions short and single-purpose
- Use descriptive variable names — no single letter variables outside of loops
- All API routes must have docstrings
- All database models must have field comments where the purpose is not obvious from the name
- Use `python-dotenv` for all configuration — no hardcoded values
- Follow Conventional Commits for all git commits:
  - `feat:` new feature
  - `fix:` bug fix
  - `chore:` tooling or config
  - `docs:` documentation only
  - `refactor:` code change with no behaviour change
  - `test:` test additions or changes

---

## Environment Variables

Copy `.env.example` to `.env` before running anything locally. Required variables:

```
ANTHROPIC_API_KEY=
MS_PLACES_TENANT_ID=
MS_PLACES_CLIENT_ID=
MS_PLACES_CLIENT_SECRET=
DATABASE_URL=sqlite:///./data/deskmate.db
ALLOCATION_RUN_TIME=23:00
CHECKIN_CUTOFF_TIME=10:00
NOTIFICATION_WEBHOOK_URL=
```

---

## Running the Project

```bash
# Install dependencies
uv sync

# Initialise the database
uv run python -m db.init

# Seed test data
uv run python -m db.seed

# Start the API
uv run uvicorn api.main:app --reload

# Start the dashboard
uv run streamlit run dashboard/app.py

# Run the allocation engine manually
uv run python -m allocation.run

# Start the agent (interactive CLI for testing)
uv run python -m agent.cli
```

---

## Demo Script (Hackathon Presentation)

1. Open agent CLI — user says "Book me a quiet desk with a monitor on Thursday"
2. Agent confirms intent, asks for building preference, writes booking to queue
3. Run allocation engine manually — show it scoring and assigning a desk
4. Show notification output confirming the desk
5. Simulate a Microsoft Places check-in event via the webhook
6. Show the checkins table updated — user is marked as present
7. Simulate a no-show for a different booking — show desk released and re-allocated
8. Open the Streamlit dashboard — show live utilisation and no-show stats
9. Agent sends feedback request — user rates the desk 4/5
10. Show the users table updated with refined preferences

---

## What We Are Not Building in This POC

- Production authentication (MS Entra SSO is mocked)
- Multi-tenancy
- Mobile app
- Email delivery (notifications are webhook / console only)
- Full MS Places hardware integration (mocked with a webhook endpoint)

These are all clear next steps and should be called out in the presentation.

---

*This file must be kept up to date as the project evolves. If you change the schema, the stack, or the architecture — update this file first.*