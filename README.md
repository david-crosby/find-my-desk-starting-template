# DeskMate — Intelligent Workspace Booking System

**Hackathon POC | Built on Microsoft Places**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![Claude API](https://img.shields.io/badge/Claude-sonnet--4--20250514-orange.svg)](https://anthropic.com)

---

## What is DeskMate?

DeskMate is an AI-powered desk and room booking system designed as a direct alternative to traditional workplace booking applications like Eptura Engage. It replaces clunky, manual booking experiences with a conversational agent that understands context, learns user preferences, and allocates workspace intelligently — much like a smart hotel concierge.

The system integrates with Microsoft Places for real-world hardware and network-based presence detection, removing the burden of manual check-in entirely.

### The Problem We're Solving

Traditional desk booking systems suffer from:
- **Forgetfulness**: People forget to book desks
- **No-shows**: People book but don't show up, leaving desks empty
- **Poor allocation**: No intelligence in matching desks to preferences
- **Manual processes**: Tedious check-in requirements
- **No learning**: Systems don't improve over time

DeskMate addresses these through intelligent automation and AI-driven personalization.

---

## Key Features

### 🤖 Conversational AI Agent
Book desks and rooms through natural language conversation. The agent understands context, resolves ambiguities, and learns from every interaction.

**Example conversations:**
- *"Book me a quiet desk near Sarah on Thursday"*
- *"I need a meeting room for 6 people tomorrow afternoon"*
- *"Update my preferences — I prefer standing desks now"*

### 🎯 Dynamic Allocation Algorithm
Instead of first-come-first-served, DeskMate uses a weighted scoring system to match users with their ideal workspace based on:
- **Personal preferences**: Noise level, lighting, equipment needs
- **Team proximity**: Sit near colleagues when possible
- **Environmental factors**: Window seats, quiet zones, accessibility
- **Historical patterns**: Learning from past bookings and feedback

### 🏨 Hotel-Style Booking Model
Bookings are queued and processed nightly by a batch allocation engine, ensuring fair, intelligent distribution rather than a race to book.

### 📍 Microsoft Places Integration
Automatic presence detection via network and hardware events. No manual check-in required — arrive and get checked in automatically.

### 📊 Management Intelligence Dashboard
Real-time insights into:
- Utilization rates by building, floor, and zone
- No-show rates and trends
- Peak demand heatmaps
- Preference analysis and trends

### 🔄 Feedback Loop
Post-visit feedback collection improves future allocations automatically.

---

## Architecture

DeskMate is built as a modular Python monorepo using modern tools:

```
DeskMate/
├── packages/
│   ├── agent/          # Claude-powered booking agent
│   ├── backend/        # FastAPI REST API
│   ├── core/           # Shared models, auth, database
│   ├── ui_admin/       # Streamlit admin dashboard
│   └── ui_user/        # Streamlit user booking interface
├── scripts/            # Database setup and utilities
└── tests/              # Test suite
```

### Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **AI Agent** | Claude API (sonnet-4-20250514) | Natural language understanding and conversation |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy | REST API and data persistence |
| **Database** | SQLite | Local data storage for POC |
| **UI** | Streamlit | Web interfaces for users and admins |
| **Scheduling** | APScheduler | Nightly allocation jobs |
| **Integration** | Microsoft Places API | Presence detection |
| **Deployment** | Local development | Container-ready for production |

---

## The AI Agent: Booking via Conversation

The core innovation of DeskMate is its conversational booking interface. Built on Anthropic's Claude API, the agent handles the full booking lifecycle through natural dialogue.

### Agent Design Principles

1. **Never ask what you can look up**: The agent silently queries user profiles, calendars, and team data before responding
2. **Context-aware**: Understands "near Sarah" by checking Sarah's booking location
3. **Tiered intelligence**: Classifies requests into 6 tiers from instant booking to complex multi-day planning
4. **Learning system**: Builds preference profiles through onboarding and feedback

### Conversation Tiers

| Tier | Trigger | Behavior |
|------|---------|----------|
| **Tier 0** | First login | Conversational onboarding to build preference profile |
| **Tier 1** | Simple requests | *"Book me a desk tomorrow"* → Execute immediately |
| **Tier 2** | Team context | *"Near the design team"* → Look up team locations |
| **Tier 3** | Equipment needs | *"Standing desk with dual monitors"* → Filter inventory |
| **Tier 4** | Multi-day | *"Book next week Tue-Thu"* → Handle date ranges |
| **Tier 5** | Complex intent | *"Quiet space for focused work"* → Infer from history |
| **Tier 6** | Changes | *"Cancel Thursday"* → Update existing bookings |

### Agent Capabilities

- **Natural language parsing**: Understands dates, locations, preferences
- **Preference learning**: Remembers user preferences across sessions
- **Multi-turn conversations**: Maintains context across messages
- **Error handling**: Graceful degradation when information is missing
- **Feedback collection**: Asks for post-visit ratings to improve matching

---

## The Allocation Algorithm: Dynamic Desk Assignment

At the heart of DeskMate is its intelligent allocation engine that matches users with optimal workspaces through weighted scoring.

### How It Works

1. **Queue bookings**: Users request desks through the agent; requests are queued, not confirmed immediately
2. **Nightly processing**: At 11 PM UTC, the allocation engine processes all pending requests
3. **Scoring and ranking**: Each available desk is scored against user preferences
4. **Optimal assignment**: Best matches are allocated and confirmed
5. **Notification**: Users receive booking confirmations via webhook/email

### Weighted Scoring Model

The algorithm calculates match scores based on multiple factors:

```python
# Maximum possible score depends on user's active preferences
max_score = 0
if user.has_preferred_neighbourhood: max_score += 50  # Primary location match
if user.prefers_window_seat: max_score += 20          # Environmental
if user.prefers_quiet: max_score += 20                # Environmental
if user.needs_standing_desk: max_score += 20          # Equipment
if user.needs_dual_monitors: max_score += 20          # Equipment
if user.needs_accessible_desk: max_score += 20        # Accessibility
if user.prefers_team_proximity: max_score += 30       # Social

# Score each available desk
for desk in available_desks:
    score = 0
    if desk.section == user.preferred_neighbourhood: score += 50
    if desk.is_window_seat and user.prefers_window_seat: score += 20
    if desk.is_quiet and user.prefers_quiet: score += 20
    if desk.has_standing_desk and user.needs_standing_desk: score += 20
    if desk.has_dual_monitors and user.needs_dual_monitors: score += 20
    if desk.is_accessible and user.needs_accessible_desk: score += 20
    if desk.section in team_sections and user.prefers_team_proximity: score += 30

    match_percentage = (score / max_score) * 100
```

### Key Algorithm Features

- **Personalization**: Scores adapt to individual preferences
- **Team awareness**: Considers colleague locations for collaboration
- **Fair allocation**: Batch processing prevents booking wars
- **Fallback handling**: If no perfect match, offers best available alternative
- **Scalability**: Efficient SQL queries with eager loading for performance

### Real-World Impact

- **Higher satisfaction**: Users get desks that match their needs
- **Better utilization**: Intelligent matching reduces no-shows
- **Reduced friction**: No more hunting for available desks
- **Data-driven**: Continuous improvement through feedback

---

## Work to Date

This is a hackathon proof-of-concept developed over 2 days by a 4-person team. Current implementation status:

### ✅ Completed Features

- **Database schema**: Complete SQLite data model with users, desks, bookings, buildings
- **AI Agent**: Full conversational booking agent with Claude integration
- **Allocation algorithm**: Weighted scoring system for desk matching
- **Backend API**: FastAPI endpoints for bookings, users, desks
- **User interface**: Streamlit app for desk/room booking
- **Admin dashboard**: Management intelligence with utilization metrics
- **Authentication**: Microsoft Entra ID SSO integration
- **Notification system**: Webhook-based booking confirmations
- **Presence detection**: Mock Microsoft Places integration
- **Feedback system**: Post-visit rating collection

### 🔄 In Progress

- **Real Microsoft Places integration**: Currently mocked; needs Azure app registration
- **Nightly scheduler**: APScheduler setup for automated allocation runs
- **Advanced analytics**: Trend analysis and forecasting
- **Mobile optimization**: Responsive UI improvements

### 🎯 Demo Objectives Achieved

1. **Auto assignment**: Dynamic allocation working end-to-end
2. **Live monitoring**: Real-time presence detection simulation
3. **AI agent**: Natural language booking fully functional
4. **MI portal**: Utilization dashboards and heatmaps
5. **Accessibility**: Dark mode and voice-friendly interfaces
6. **Executive features**: Exclusion lists and delegate booking

### 🏗️ Architecture Decisions

- **Python monorepo**: Modular packages with shared core
- **SQLite for POC**: Local file-based DB for easy setup
- **Claude for AI**: Superior reasoning for complex booking logic
- **Streamlit for UI**: Rapid prototyping with good UX
- **FastAPI backend**: Modern async API with auto-docs
- **Hotel model**: Queue-and-allocate prevents booking conflicts

---

## Setup Instructions

### Prerequisites

- Python 3.12
- uv package manager
- Anthropic API key (for Claude agent)

### Quick Start

1. **Clone and setup:**
   ```bash
   git clone <repo-url>
   cd find-my-desk-starting-template/DeskMate
   cp .env.example .env
   # Edit .env with your ANTHROPIC_API_KEY
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Initialize database:**
   ```bash
   uv run python scripts/init_db.py
   uv run python scripts/seed_demo.py
   ```

4. **Start services:**
   ```bash
   # Terminal 1: Backend API
   uv run uvicorn places_backend.main:app --reload --port 8000

   # Terminal 2: Agent server
   uv run python -m places_agent.server

   # Terminal 3: User UI
   uv run streamlit run places_ui_user/app.py --server.port 8501

   # Terminal 4: Admin UI
   uv run streamlit run places_ui_admin/app.py --server.port 8502
   ```

5. **Access applications:**
   - User booking: http://localhost:8501
   - Admin dashboard: http://localhost:8502
   - API docs: http://localhost:8000/docs

### Configuration

Key environment variables:
- `ANTHROPIC_API_KEY`: Required for AI agent
- `DATABASE_URL`: SQLite path (default works)
- `AZURE_TENANT_ID`: For real Microsoft integration (optional)

---

## Usage Examples

### Booking a Desk
1. Open user interface at http://localhost:8501
2. Login with Microsoft account
3. Chat with agent: *"Book me a quiet desk near the window for tomorrow"*
4. Agent confirms booking and queues for nightly allocation
5. Receive confirmation notification next day

### Viewing Analytics
1. Open admin dashboard at http://localhost:8502
2. View utilization rates, heatmaps, and booking trends
3. Monitor no-show rates by team and individual

### Managing Preferences
- Agent learns preferences through onboarding
- Update via conversation: *"I prefer standing desks now"*
- View profile in admin interface

---

## Team

- **Scott**: AI agent development and Claude integration
- **David**: Backend architecture, database design, API development
- **Jack**: Management intelligence dashboard and analytics
- **Hans**: UI/UX design, user experience optimization

---

## Future Roadmap

- **Production deployment**: Containerization with Docker/Kubernetes
- **Advanced AI**: Multi-modal inputs (voice, calendar integration)
- **Mobile app**: Native iOS/Android applications
- **Advanced analytics**: Predictive booking patterns, demand forecasting
- **Enterprise features**: Multi-tenant support, custom workflows
- **Integration expansion**: Outlook calendar sync, Teams notifications

---

## Contributing

This is a hackathon project — contributions welcome! Focus areas:
- Algorithm improvements
- UI/UX enhancements
- Additional integrations
- Performance optimizations

Built with ❤️ at [Hackathon Name] using Claude Code and modern Python tooling.