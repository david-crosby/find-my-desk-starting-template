# DeskMate — Conversation Tiers & Agent Design

> This document defines the full conversation tier model for the DeskMate AI booking assistant.
> It covers every interaction pattern from first-time profile setup through to intelligent,
> proactive desk suggestions. Use this as the foundational spec when building the agent layer.

---

## Overview

DeskMate uses a tiered intent model to classify and handle every user utterance. Each tier
represents a distinct type of booking interaction, increasing in complexity and context-awareness.
The agent resolves as many slots as possible silently before responding — it should never ask
for information it can look up.

| **Tier** | **Label** | **Trigger** | **Agent behaviour** |
| --- | --- | --- | --- |
| Tier 0 | Profile setup | First login / `onboarding_completed = false` | Conversational onboarding — builds preference profile |
| Tier 1 | Instant booking | Single date/location request | Execute and confirm — no clarification needed |
| Tier 2 | Social & team context | Reference to colleagues or meetings | Look up workplans silently, then suggest |
| Tier 3 | Preferences & requirements | Equipment, environment, accessibility | Filter desk inventory before presenting options |
| Tier 4 | Recurring & multi-day | Patterns, sprints, weekly cadence | Resolve all dates, surface conflicts, confirm full set |
| Tier 5 | Intelligent & inferential | Vague or high-level intent | Read calendar + workplans + history, then propose |
| Tier 6 | Amendments & cancellations | Change, cancel, or status check | Look up existing bookings first, confirm before bulk actions |

### Core principle

> **Never ask for information you can look up.**
> If the user says "near Sarah on Thursday", query Sarah's workplan silently — do not ask which building she's in.

### Slots the agent always tries to resolve

| **Slot** | **Description** |
| --- | --- |
| **When** | Date, time, duration, recurrence pattern |
| **Where** | Building, floor, section, near whom |
| **Why** | Meeting context, focus work, collaboration |
| **Needs** | Equipment, accessibility, environment |
| **Who else** | Named colleagues, team members, visitors |
| **Confidence** | Book immediately vs. propose first |

---

## Tier 0 — Profile setup

### Purpose

Triggered on first login or when `onboarding_completed = false`. The agent runs a structured
but conversational onboarding to build a preference profile that powers every future interaction.
Takes approximately 3–4 minutes. All answers are stored and applied silently in Tiers 1–6.

### Agent system note

```
If onboarding_completed = false:
  Run Tier 0 before processing any booking request.
  If user skips, set onboarding_skipped = true and re-prompt on next 2 sessions.
  Partial profiles are still useful — do not block booking if onboarding is incomplete.
```

### Step 0.1 — Hub & anchor days

**Agent opening:**

> "Hi! I'm your new desk booking assistant. Before I can start finding you the perfect spot,
> I'd love to learn a bit about how you like to work. It'll only take a few minutes and you'll
> never have to repeat yourself. Let's start with the basics — which office is your home base?"

**Questions to resolve:**

- Which office is your primary location?
- Which days do you typically come in? (anchor days)
- What time do you usually arrive and leave?

**Example utterances:**

- "My main office is the London Paddington site"
- "I'm in every Tuesday and Thursday — that's pretty fixed"
- "It varies week to week depending on meetings"
- "I try to come in at least two days a week but I'm flexible on which"
- "I'm usually in by 8am and leave around 5"

**Database fields populated:**

- `home_building_id`
- `team_anchor_days`
- `default_arrival_time`
- `default_departure_time`

---

### Step 0.2 — Office buddies & team

**Agent prompt:**

> "Great. One of the most useful things I can do is make sure you end up near the right people
> when you come in. Who are the colleagues you most want to be close to?"

**Questions to resolve:**

- Which colleagues do you want to sit near?
- Whose office plans should the agent monitor?
- Can anyone book on your behalf?

**Example utterances:**

- "I always like to be near Sarah from product and James from engineering"
- "Just keep me near my immediate team — the Growth squad"
- "Track my whole team — I want to know when they're in"
- "Just track a few key people: my manager and two or three others"
- "Yes, my EA Emma can book for me"

**Database fields populated:**

- `follow_colleagues`
- `team_section_id`
- `delegate_booking_ids`

---

### Step 0.3 — Preferred desk location

**Agent prompt:**

> "Do you have a preferred area of the building, or a particular floor you gravitate towards?"

**Questions to resolve:**

- Is there a preferred floor or building zone?
- Do you have favourite desks you always return to?
- Are there areas you want to avoid?

**Example utterances:**

- "I prefer to be high up — floor 4 or above if possible"
- "I love the desks by the window on Floor 3 north side"
- "I have a specific desk I always use — Desk 4B-12"
- "Avoid the desks right next to the kitchen — too noisy"
- "I don't want to be in the open collaboration zone"

**Database fields populated:**

- `home_floor_id`
- `home_section_id`
- `favourite_desk_ids`

---

### Step 0.4 — Environment & workspace feel

**Agent prompt:**

> "Tell me about the kind of environment you work best in. There's no wrong answer."

**Questions to resolve:**

- Preferred noise level
- Natural light preference
- Temperature sensitivity
- Open plan vs. enclosed space

**Example utterances:**

- "I need it quiet — I do a lot of focused work and calls"
- "A bit of background buzz is fine, I like the energy"
- "Natural light is important to me — window seat if possible"
- "I run warm — I prefer cooler areas away from heating vents"
- "I prefer a pod or focus booth — I need to concentrate"

**Database fields populated:**

- `preferred_noise_level`
- `preferred_light`
- `preferred_temperature`
- `preferred_section_type`
- `prefers_window_seat`

---

### Step 0.5 — Equipment & accessibility needs

**Agent prompt:**

> "Are there any desk features or equipment that you need, or that would make a big difference to your day?"

**Questions to resolve:**

- Hardware requirements (monitors, docking station, standing desk)
- Accessibility requirements
- Nearby amenity preferences (parents' room, prayer room, bike storage, showers)

**Example utterances:**

- "I need a docking station and at least one external monitor"
- "Dual monitors please — I work across a lot of windows"
- "A sit-stand desk would be great if one's available"
- "I need a wheelchair-accessible desk near a lift"
- "It's important I'm near the parents' room"
- "Near the bike storage and showers — I cycle in"

**Database fields populated:**

- `docking_station_required`
- `dual_monitor_required`
- `requires_standing_desk`
- `accessible_desk`
- `ergonomic_chair_required`
- `near_amenity`

---

### Step 0.6 — Agent behaviour & notifications

**Agent prompt:**

> "Last step — how do you want me to behave? Some people want me to just get on with it;
> others prefer to confirm before I do anything."

**Questions to resolve:**

- Booking autonomy level
- Preferred notification channel
- Reminder preferences
- Calendar sync

**Example utterances:**

- "Just book it — if you find something good, go ahead without asking"
- "Suggest what you'd pick, then wait for me to confirm"
- "Always show me options first — I'll choose"
- "Send me a Teams message when a booking is confirmed"
- "Yes, add all my desk bookings to my Outlook calendar"
- "Remind me the evening before I'm booked in"

**Database fields populated:**

- `ai_autonomy_level`
- `notification_channel`
- `notify_on_create`
- `notify_on_reminder`
- `calendar_sync_enabled`
- `onboarding_completed`

### What a complete Tier 0 profile unlocks

| **Tier** | **What becomes possible** |
| --- | --- |
| Tier 1 | Books with zero clarifying questions — date is the only input needed |
| Tier 2 | Silently checks buddies' workplans before making a suggestion |
| Tier 3 | Pre-filters desk inventory by equipment and environment on every search |
| Tier 4 | Knows anchor days so recurring bookings need a single confirmation |
| Tier 5 | Proactively suggests office days without being asked |
| Tier 6 | Sends cancellation confirmations via the preferred channel automatically |

---

## Tier 1 — Instant booking

### Purpose

The user knows what they want and just needs it done. One or two pieces of information are
present in the utterance. No clarification should be needed if Tier 0 is complete.

### Agent behaviour

```
1. Extract date and duration from utterance
2. Default location to home_building_id from profile
3. Check calendar for conflicts on that date
4. Find best available desk matching saved preferences
5. Book and confirm — do not ask for permission
```

### Example utterances

**Date & location:**

- "Book me a desk tomorrow"
- "I need a desk in the London office on Friday"
- "Get me a spot for next Monday morning"

**Half-day & time:**

- "Book a desk for just this afternoon, I'll be in around 1pm"
- "I only need a desk in the morning next Tuesday"

### Minimum slots required

| **Slot** | **Required** | **Default if missing** |
| --- | --- | --- |
| Date | Yes | Ask once |
| Duration | No | `default_booking_duration` from profile |
| Location | No | `home_building_id` from profile |

### Edge cases

- "Same desk as last time" → look up `recently_used_desk_ids`, check availability, propose it
- "Just book something" → use profile defaults across all slots

---

## Tier 2 — Social & team context

### Purpose

The user wants to be near specific people or align with their team's plans. The agent must
look up colleague workplans via the MS Places presence API before booking.

### Agent behaviour

```
1. Identify named colleagues or team references in utterance
2. Call get_team_workplans(date) to find where they are booked
3. Identify their floor/section from booking records
4. Find closest available desk to that location
5. Propose with explanation — "Sarah is on Floor 3 North on Thursday, I've found a desk two rows away"
```

### Example utterances

**Near colleagues:**

- "Book me a desk near Sarah on Thursday"
- "Find me something close to the product team next Wednesday"
- "Where is most of my team sitting next week? Book me in with them"

**Meeting-driven:**

- "I have the all-hands in Meeting Room 3 at 2pm — book me a desk nearby for the rest of the day"
- "I'm coming in for a client meeting on Floor 4. Can you sort a desk for the morning?"

### Agent tools called silently

- `get_team_workplans(date)` — find where colleagues are booked
- `get_user_calendar(date)` — identify meeting room location for proximity logic

---

## Tier 3 — Preferences & requirements

### Purpose

The user has specific needs — equipment, environment, or accessibility. The agent applies
these as hard filters on the desk inventory before presenting options.

### Agent behaviour

```
1. Extract requirement from utterance (or apply saved profile preferences)
2. Build filter set: desk_mode, amenities, section_type, accessibility flags
3. Call list_available_desks(date, filters)
4. Return best match — explain why it was chosen if non-obvious
```

### Example utterances

**Equipment & setup:**

- "I need a desk with a monitor and docking station next Monday"
- "Book me somewhere quiet — ideally a focus pod or phone booth area on Friday"
- "Can you find a standing desk for Wednesday?"

**Accessibility & environment:**

- "I need a wheelchair-accessible desk near a lift on Thursday"
- "Somewhere with natural light please for Monday"
- "I need to be on a floor with a parents' room close by next week"

### Filter fields used

- `docking_station_required`
- `dual_monitor_required`
- `requires_standing_desk`
- `accessible_desk`
- `preferred_section_type`
- `near_amenity`
- `preferred_noise_level`

---

## Tier 4 — Recurring & multi-day

### Purpose

The user wants a pattern of bookings, not a one-off. The agent must resolve all dates,
check availability across each one, and confirm the full set before booking.

### Agent behaviour

```
1. Parse recurrence pattern from utterance (days of week, date range, or named period)
2. Resolve all individual dates
3. Check availability for each date independently
4. Surface any conflicts or unavailable dates before confirming
5. Present the full list: "That's 9 bookings across 3 weeks — here's what I found..."
6. Book only after explicit confirmation
7. Prefer the same desk across the series where possible
```

### Example utterances

**Weekly patterns:**

- "Book me a desk every Tuesday and Thursday for the next month"
- "I'm in the office every Wednesday — set up a recurring booking for the rest of the quarter"

**Trip / project block:**

- "I'm in the Edinburgh office all of next week — book me a desk Mon to Fri, same spot if possible"
- "We have a project sprint 14–18 July. Can you block a desk for the whole team for those 5 days?"

### Rules

- [ ]  Always surface conflicts before booking — never silently skip a date
- [ ]  Confirm full list before executing any bookings
- [ ]  Attempt desk consistency across the series (`always_book_same_desk`)
- [ ]  For team bookings, check each member's `restricted_to_groups` policy

---

## Tier 5 — Intelligent & inferential

### Purpose

Vague or high-level intent. The agent must read the user's calendar, team workplans, and
preference history to reason about what they actually need — then propose rather than just execute.

### Agent behaviour

```
1. Call get_user_calendar() for the relevant period
2. Call get_team_workplans() to assess who is in and when
3. Call get_building_occupancy() for any "is it busy?" signals
4. Cross-reference with preference history and anchor days
5. Generate a reasoned suggestion: "Based on your calendar and team plans, Wednesday looks best..."
6. Propose — do not book without confirmation at this tier
```

### Example utterances

**Calendar-aware:**

- "Sort out my office days next week — you know what I normally like"
- "I've got back-to-back meetings in the office on Thursday — make sure I'm not running between floors"
- "Look at my calendar and suggest the best days to come in this week based on who else is in"

**Proactive & advisory:**

- "Is it worth coming in on Friday or will it be dead?"
- "I haven't been in for two weeks — find me a good day and just book it"
- "My team tends to be in on Wednesdays. Check if that's the case next week and book me in if so"

### Data sources required

| **Source** | **Used for** |
| --- | --- |
| `get_user_calendar(date)` | Identify meeting locations and conflicts |
| `get_team_workplans(date)` | Assess team presence by day |
| `get_building_occupancy(date)` | Answer "is it busy?" queries |
| `get_booking_history()` | Understand patterns and preferred desks |
| User preference profile | Apply saved defaults without asking |

---

## Tier 6 — Amendments & cancellations

### Purpose

Post-booking actions. The agent must always look up existing reservations before acting.
Single cancellations execute immediately; bulk cancellations require confirmation.

### Agent behaviour

```
For amendments:
  1. Look up existing booking by date or description
  2. Identify what needs to change (date, time, location)
  3. Check availability for new slot
  4. Cancel old booking and create new one atomically
  5. Confirm the change

For cancellations (single):
  1. Look up booking
  2. Cancel immediately
  3. Confirm with details

For cancellations (bulk — 2 or more):
  1. Look up all matching bookings
  2. Present the full list to the user
  3. Ask for explicit confirmation
  4. Only then cancel all

For status checks:
  1. Query bookings table for user
  2. Return structured summary
```

### Example utterances

**Change:**

- "I'm now coming in on Wednesday instead of Thursday — can you move my booking?"
- "I need to stay later than planned — extend my desk booking to 7pm today"

**Cancel:**

- "I'm working from home tomorrow — please cancel my desk booking"
- "Cancel all my desk bookings for next week — plans have changed"

**Status check:**

- "What desk am I booked on this week?"
- "Do I have anything booked in the next two weeks?"

### Rules

- [ ]  Never permanently delete — set `status = cancelled`, retain for audit
- [ ]  Bulk cancellations (2+) always require explicit user confirmation
- [ ]  Store `cancellation_reason = user_cancelled` on the booking record
- [ ]  Notify via `notification_channel` from profile on cancellation

---

## Agent system prompt

Use this as the base system prompt for the DeskMate agent.

```
You are DeskMate, a smart desk booking assistant integrated with Microsoft Places.
Your job is to understand what the user needs and book a desk on their behalf
via the Microsoft Graph API.

CONTEXT AVAILABLE TO YOU — call these tools silently before responding:
  get_user_profile()                   → home office, floor, equipment, preferences
  get_user_calendar(date)              → meetings, room locations, travel that day
  get_team_workplans(date)             → which colleagues plan to be in and where
  get_booking_history()                → previously used desks and patterns
  list_available_desks(date, filters)  → live availability from Places API
  get_building_occupancy(date)         → forecast busyness by floor and section

RULES:
  1.  Classify every utterance into a Tier (0–6) before responding.
  2.  Extract as many slots as possible from context before asking anything.
  3.  Ask at most ONE clarifying question per turn. Combine ambiguities.
  4.  Tier 1: execute and confirm. Do not ask for permission twice.
  5.  Tier 4: propose the full list, then wait for confirmation before booking.
  6.  Tier 6 bulk cancellations: always confirm before executing.
  7.  If a preferred desk is unavailable, offer the closest alternative with an explanation.
  8.  Always surface conflicts before completing a booking — never after.
  9.  Respond in the same register as the user — casual if casual, precise if precise.
  10. Never ask for information you can look up from profile or calendar.
```

---

## Edge case handling

| **User says** | **Agent should** |
| --- | --- |
| "Same desk as last time" | Query `recently_used_desk_ids`, check availability, propose it |
| "Somewhere near the coffee" | Map section labels from IMDF data, fall back to "near the kitchen on Floor 2" |
| "Just sort it" | Use profile + calendar + workplans to pick best day, propose with reasoning |
| "Is it busy?" | Pull `floor_forecast_occupancy`, respond in plain English |
| "My usual spot" | Resolve from `favourite_desk_ids` — if empty, ask once and store the answer |
| "Book for me and the team" | Tier 4 flow — resolve each team member, check each desk, confirm full list |
| No profile set | Route to Tier 0 before processing the request |

---

## Database fields referenced by tier

| **Field** | **Tier 0** | **Tier 1** | **Tier 2** | **Tier 3** | **Tier 4** | **Tier 5** | **Tier 6** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `home_building_id` | Write | Read | Read | Read | Read | Read | |
| `team_anchor_days` | Write | | | | Read | Read | |
| `follow_colleagues` | Write | | Read | | | Read | |
| `favourite_desk_ids` | Write | Read | | | Read | | |
| `ai_autonomy_level` | Write | Read | Read | Read | Read | Read | Read |
| `preferred_noise_level` | Write | | | Read | | | |
| `docking_station_required` | Write | | | Read | | | |
| `near_amenity` | Write | | | Read | | | |
| `notification_channel` | Write | | | | | | Read |
| `calendar_sync_enabled` | Write | Read | | | | | |
| `onboarding_completed` | Write | | | | | | |
| `booking_source` | | Write | Write | Write | Write | Write | Write |
| `agent_intent_tier` | | Write | Write | Write | Write | Write | Write |
| `slots_extracted` | | Write | Write | Write | Write | Write | Write |
| `slots_inferred` | | Write | Write | Write | Write | Write | Write |
| `clarification_turns` | | Write | Write | Write | Write | Write | Write |

---

## Related documentation

- `SCHEMA.md` — full database field definitions across all eight categories
- `GRAPH_API.md` — Microsoft Graph API endpoints and authentication setup
- `TENANT_SETUP.md` — PowerShell prerequisites and Places directory configuration
- `METRICS.md` — analytics metrics, data sources, and recommended displays
