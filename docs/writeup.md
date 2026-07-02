# MeetSmart AI — Platform Write-up

## Overview

**MeetSmart AI** is an internal, self-hosted meeting management platform built for ThinkPalm Technologies. It eliminates dependency on paid external tools (Calendly, Doodle, Otter.ai) by providing an integrated, AI-powered system for the entire meeting lifecycle — from scheduling to post-meeting follow-up.

## Problem Statement

ThinkPalm engineering and product teams spend significant time on meeting coordination overhead: finding common slots across participants, drafting agenda emails, writing meeting notes, creating action-item trackers, and sending follow-up reminders. These activities are fragmented across multiple tools and emails, leading to missed action items, poor documentation, and scheduling conflicts.

## Solution Architecture

MeetSmart AI introduces a **multi-agent architecture** where six specialized AI agents handle each phase of the meeting lifecycle:

| Agent | Responsibility |
|---|---|
| **Availability Agent** | Reads/writes SQLite schedule store; surfaces open slots for N employees; powers the availability grid |
| **Booking Agent** | Checks all participants' schedules; selects the optimal (earliest) common slot; creates confirmed meeting record |
| **Invite Agent** | Auto-generates RFC 5545 compliant `.ics` calendar files with agenda and participants; emails via SMTP |
| **Notes Agent** | Ingests meeting transcript; calls Gemini LLM (or rule-based parser); extracts summary, decisions, action items with owners |
| **MoM Agent** | Generates branded Word (.docx) Minutes of Meeting document; saves with date-stamped filename; emails to all participants |
| **Reminder Agent** | Uses APScheduler to send 24h and 1h pre-meeting reminders; 24h post-meeting action item follow-up emails |

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React 18, Vite 5, Vanilla CSS |
| Backend API | FastAPI 0.111, Uvicorn |
| Database | SQLite (via SQLAlchemy ORM) |
| LLM | Google Gemini 1.5 Flash (free tier) + rule-based fallback |
| Calendar | `icalendar` Python library (RFC 5545) |
| Word Documents | `python-docx` |
| Scheduling | APScheduler |
| Email | SMTP (Gmail / mock console) |
| Architecture Diagram | `diagrams` Python library |

All tools are 100% free and open-source. No cloud infrastructure or paid APIs required (Gemini free tier sufficient).

## Key Design Decisions

1. **SQLite over PostgreSQL** — Zero-config setup, sufficient for a team-sized deployment, easily replaceable with Postgres via SQLAlchemy URL change.

2. **Gemini with rule-based fallback** — The system works fully without a Gemini API key. Rule-based extraction uses regex patterns and heuristics, ensuring the prototype is always demonstrable.

3. **Mock SMTP** — Default mode prints emails to console with full HTML formatting, making demo recording easy without email server setup.

4. **Background tasks for I/O** — Invite sending and MoM generation use FastAPI `BackgroundTasks` to return immediately to the UI while processing continues asynchronously.

5. **APScheduler embedded in FastAPI** — Eliminates the need for a separate Celery/Redis stack for the prototype while maintaining reliable reminder scheduling.
