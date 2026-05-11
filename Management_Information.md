## Introduction

This document outlines the proposed analytics and reporting model for the Desk Booking Platform. The solution is designed to provide both real-time operational visibility and longer-term behavioural insights across workspace usage, booking patterns, collaboration trends, facilities management, and AI-assisted booking experiences.

The platform uses two separate data pipelines:

- A real-time pipeline for live desk availability, utilisation, and occupancy insights
- A nightly batch pipeline for trend analysis, rolling averages, and behavioural reporting

Most analytics are powered directly from the internal bookings database, with a small number of Microsoft Graph API integrations used to enrich desk inventory, occupancy telemetry, and organisational team data.

The goal is to provide actionable insights for employees, workplace teams, facilities management, and product owners while creating a scalable foundation for future AI-driven workplace optimisation.

## Architecture

Two separate analytics pipelines:

### Real-time (hourly refresh)
- Free desks available
- Live utilisation
- Floor hotspot maps

### Nightly batch processing
- No-show trends
- Team co-location insights
- AI agent performance metrics

## Required Microsoft Graph APIs

- `GET /places/microsoft.graph.desk` — desk inventory
- `GET /workplace/sensorDevices` — occupancy status
- `POST /workplace/sensorDevices/{id}/ingestTelemetry` — sensor telemetry ingestion
- `GET /groups/{id}/members` — team membership sync

> All remaining analytics come from the internal bookings database.

---

## Key Analytics Areas

### Workspace Utilisation
- No-show trends (4-week rolling average)
- Live floor utilisation and hotspot mapping
- Real-time free desk availability

### Booking Behaviour
- Advance booking patterns
- Cancellation timing and no-show rates
- Repeat desk usage / desk loyalty
- Peak booking request times

### Team & Collaboration Insights
- Team co-location frequency
- Collaboration density (teams physically sitting together)
- “Ghost floor” detection:
  - Floors heavily booked but lightly occupied

### AI Agent Performance
- First-suggestion acceptance rate
- Clarification turns per booking
- Fallback / failure rate trends

### Facilities & Operations
- Auto-release frequency by desk
- Check-in compliance
- Desk downtime tracking
- Sustainability and energy correlation metrics

---

## Recommended Visualisations

- Trend lines and KPI cards
- Live floor heatmaps
- Booking behaviour bar charts
- Team/day heatmaps
- Ranked operational tables
- Calendar-based occupancy views
