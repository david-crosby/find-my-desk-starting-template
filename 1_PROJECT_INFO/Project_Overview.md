# DeskMate — Intelligent Workspace Booking System

**Hackathon POC | Built on Microsoft Places**

---

## What We Are Building

DeskMate is an AI-powered desk and room booking system designed as a direct alternative to Eptura Engage. It replaces the rigid, manual booking experience with a conversational agent that understands context, learns user preferences, and allocates workspace intelligently — much like a smart hotel concierge.

The system integrates with Microsoft Places for real-world hardware and network-based presence detection, removing the burden of manual check-in entirely.

---

## The Problem We Are Solving

Traditional desk booking applications, such as Eptura Engage, are clunky. People forget to book. People book and do not show up. Desks sit empty while colleagues cannot find a space. There is no intelligence, no learning, no feedback loop, and they have too many behavioural dependencies to work effectively.

DeskMate changes this by:

- Understanding bookings through natural language, not forms
- Learning from each user's preferences, working patterns, and anchor days
- Automatically allocating the best available desk or room each night
- Detecting physical presence through Microsoft Places (network and hardware)
- Freeing up no-show desks automatically for re-use
- Asking for feedback after each visit and improving over time

---

## Core System Components

### 1. Conversational AI Agent

The entry point for every user interaction. Built using the Claude API (`claude-sonnet-4-20250514`), the agent accepts natural language requests and translates them into structured booking intents. It handles:

- New booking requests — *"Book me a quiet desk near the window on Thursday"*
- Preference updates — *"I prefer standing desks and dual monitors"*
- Cancellations and amendments
- Post-visit feedback collection

### 2. Booking Queue and Nightly Allocation Engine

Bookings are not confirmed in real time. Instead they are queued and processed nightly by a Python batch job. This engine:

- Reads all pending bookings for the following day
- Scores and ranks available desks against user preferences — location, equipment, proximity to team, anchor days, and environmental factors such as noise level and lighting
- Allocates the best match and confirms it to the user
- Handles re-allocation if a booking is released due to a no-show

This model mirrors how hotels operate and ensures fair, intelligent allocation rather than a first-come-first-served race.

### 3. SQLite Data Layer

For the purposes of this POC, all data is stored in a local SQLite database. Tables include:

| Table | Purpose |
|---|---|
| `users` | User profiles and preferences |
| `buildings` | Building and floor metadata |
| `desks` | Desk inventory with attributes — location, equipment, desk type, zone |
| `rooms` | Room inventory with capacity and AV equipment |
| `bookings` | Queued and confirmed bookings |
| `allocations` | Nightly allocation results |
| `checkins` | Presence detection events from Microsoft Places |
| `feedback` | Post-visit ratings and comments |

### 4. Microsoft Places Integration

DeskMate connects to Microsoft Places to detect physical presence without requiring any user action. When a user arrives, their network connection or badge and hardware event is received, the system marks them as checked in and records the visit. If they do not appear by a configurable cut-off time, the desk is released back into the pool for same-day re-use.

### 5. Notification Service

Once the nightly allocation runs, users are notified of their confirmed desk or room. Notifications are delivered via a simple webhook or simulated message for the POC. The user receives their desk number, floor, building, and any relevant instructions.

### 6. Management Intelligence Dashboard

A lightweight Python web UI providing:

- Daily and weekly utilisation rates by building, floor, and zone
- No-show rates by team and individual
- Peak demand heatmaps
- Preference trend analysis

### 7. Feedback Loop

After each visit the agent follows up with the user. Feedback is stored and used to update their preference profile, improving the quality of future allocations automatically.

---

## Technology Stack

| Layer | Technology |
|---|---|
| AI Agent | Claude API — `claude-sonnet-4-20250514` |
| Backend Services | Python 3.12, uv |
| API Layer | FastAPI |
| Database | SQLite via SQLAlchemy |
| UI and Dashboard | Streamlit |
| Workplace Integration | Microsoft Places API |
| Workplace Integration Limited To| Microsoft E5 Licence |
| Scheduling | APScheduler |
| Notifications | Webhook / mock (POC) |
| Configuration | python-dotenv |

---

## What Makes This Exceptional

- **No check-in friction** — Microsoft Places handles presence automatically
- **Intelligent allocation, not just booking** — the nightly engine optimises for the whole organisation, not just the individual
- **Self-improving** — user preferences evolve based on feedback
- **Re-use logic** — no-show desks are freed and re-offered the same day
- **MI from day one** — utilisation data is captured from the very first booking
