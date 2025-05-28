# Architecture Overview

This document provides a technical overview of the CommercialBreaker & Toonami Tools system architecture, component relationships, and data flow.

## System Overview

CommercialBreaker & Toonami Tools is a modular Python application designed to automate the creation of Toonami-style anime marathon channels. The system processes anime episodes, detects commercial break points, and integrates authentic Toonami bumps to create seamless viewing experiences.

### Core Philosophy

- **Modular Design**: Each tool handles a specific aspect of the pipeline
- **Database-Driven**: SQLite manages metadata and processing state
- **Interface Flexibility**: Multiple UIs for different use cases
- **Platform Agnostic**: Works with various media servers and channel platforms

---

## Application Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Entry Point (main.py)                   │
├─────────────────────────────────────────────────────────────┤
│Interface Selection: --tom | --webui | --clydes | --combreak │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────┬─────────────────┬─────────────────┐
│   GUI Layer     │   Web Layer     │   CLI Layer     │
│                 │                 │                 │
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌─────────────┐ │
│ │ TOM.py      │ │ │Absolution.py│ │ │ clydes.py   │ │
│ │ (Tkinter)   │ │ │ (REMI/Web)  │ │ │ (Console)   │ │
│ └─────────────┘ │ └─────────────┘ │ └─────────────┘ │
└─────────┬───────┴─────────┬───────┴─────────┬───────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐           ┌────────────────────────────────────────────────────────────┐
│               FrontEndLogic.py (Orchestrator API)           │           │              Supporting API Modules                        │
├─────────────────────────────────────────────────────────────┤===========├──────────────────────────┬─────────────────────────────────┤
│ • LogicController class - Central API for all UIs           │           │   FlagManager.py         │  messagebroker.py               │
│ • State management via SQLite database                      │           │ • Platform compatibility │ • Real-time communication       │
│ • Threading for background operations                       │           │ • Global Flags           │ • In-memory pub/sub             │
└─────────────────────────────────────────────────────────────┘           └──────────────────────────┴─────────────────────────────────┘
                               │
                               ▼

┌─────────────────────────────────────────────────────────────┐
│                   Core Processing Layer                     │
├─────────────────┬─────────────────┬─────────────────────────┤
│   ComBreak/     │ ToonamiTools/   │     ExtraTools/         │
│                 │                 │                         │
│ • Commercial    │ • Show Detection│ • Manual Tools          │
│   Detection     │ • Lineup        │ • Utilities             │
│ • File Cutting  │   Generation    │ • Debugging             │
│ • Cutless Mode  │ • Bump Encoding │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data & Integration Layer                 │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Database      │   Plex API      │   Platform APIs         │
│   (SQLite)      │                 │                         │
│                 │ • Authentication│ • DizqueTV REST         │
│ • Show Metadata │ • Library Scan  │ • Tunarr Integration    │
│ • Bump Catalog  │ • Timestamps    │                         │
│ • Lineup State  │ • File Paths    │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## In-Memory Message Broker

A unified in-memory message broker is responsible for all real-time communication between the LogicController and the various user interfaces (GUI, Web, CLI).

- **Channel-Based Communication**: All UIs subscribe to relevant channels for updates and publish user actions/events.
- **Decoupled Integration**: Interfaces interact with the LogicController exclusively through the message broker, ensuring modularity and testability.

---

## Data Flow

### 1. Initialization Phase

```
User Input → Interface Selection → Configuration Loading → Plex Authentication
```

### 2. Content Discovery Phase

```
Plex Library Scan → Show Detection (IMDB/Wikipedia) → Bump Analysis → Database Population
```

### 3. Processing Phase

```
Episode Selection → Commercial Detection → File Processing → Metadata Generation
```

### 4. Integration Phase

```
Lineup Generation → Platform Channel Creation → Playback Optimization
```

---

This architecture supports the system's goals of modularity, reliability, and extensibility while maintaining the performance necessary for processing large media libraries efficiently.
