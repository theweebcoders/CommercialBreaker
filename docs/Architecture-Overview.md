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
┌─────────────────────────────────────────────────────────────┐          
│               FrontEndLogic.py (Orchestrator API)           │
├─────────────────────────────────────────────────────────────┤
│ • LogicController class - Central API for all UIs           │           
│ • State management via SQLite database via DataManager      │
│ • Threading for background operations                       │
└─────────────────────────────────────────────────────────────┘           
        │    │  ▲          │    ▲
        │    │  │          │    │
        │    │  │          ▼    │  
        │    │  │   ┌───────────────────────────────────────────────────────────┐
        │    │  │   │                  Supporting API Modules                   │
        │    │  │   ├──────────────────────────┬────────────────────────────────┤
        │    │  │   │  FlagManager.py          │  MessageBroker.py              │ 
        │    │  │   │ • Platform compatibility │ • Real-time communication      │
        │    │  │   │ • Global Flags           │ • In-memory pub/sub            │
        │    │  │   ├──────────────────────────┼────────────────────────────────┤
        │    │  │   │      Reserved Box        │  ErrorManager.py               │
        │    │  │   │                          │ • Centralized error handling   │
        │    │  │   │   for Future Use         │ • Error history tracking       │
        │    │  │   │                          │ • UI error broadcasting        │
        │    │  │   └──────────────────────────┴────────────────────────────────┘
        │    │  │                                               ▲ 
        │    ▼  │                                               │
        │  ┌────────────────────────────────────────────────┐   │
        │  │                    Database                    │   │ 
        │  ├────────────────────────────────────────────────┤   │
        │  │ DatabaseManager.py                             │   │
        │  ├────────────────────────────────────────────────┤   │
        │  │ • Thread-safe connections • Transaction support│   │
        │  │ • Automatic retry logic   • Simplified API     │   │
        │  └────────────────────────────────────────────────┘   │
        │     ▲  │                                              │
        │     │  │                ┌─────────────────────────────┘
        ▼     │  ▼                │
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
┌───────────────────────────────────────┐
│      Platform Integration Layer       │
├─────────────────┬─────────────────────┤
│   Plex API      │   Platform APIs     │
│                 │                     │
│ • Authentication│ • DizqueTV REST     │
│ • Library Scan  │ • Tunarr Integration│
│ • Timestamps    │                     │
│ • File Paths    │                     │
└─────────────────┴─────────────────────┘

---

## In-Memory Message Broker

A unified in-memory message broker is responsible for all real-time communication between the LogicController and the various user interfaces (GUI, Web, CLI).

- **Channel-Based Communication**: All UIs subscribe to relevant channels for updates and publish user actions/events.
- **Decoupled Integration**: Interfaces interact with the LogicController exclusively through the message broker, ensuring modularity and testability.

## Database Management

The CommercialBreaker uses a centralized DatabaseManager for all database operations, providing:

- **Thread-safe connections**: Each thread gets its own database connection
- **Automatic retry logic**: Handles database locks with exponential backoff
- **Transaction support**: Atomic operations with automatic commit/rollback
- **Simplified API**: Common operations wrapped in convenient methods

All modules access the database through `get_db_manager()` from `API.utils.DatabaseManager`. This ensures consistent error handling and prevents database lock issues in multi-threaded scenarios.

## Centralized Error Handling

The system employs a centralized error handling mechanism via `ErrorManager.py`, which provides:
- **Global Error Tracking**: All errors are logged and can be retrieved by any interface
- **UI Broadcasting**: Errors can be sent to all interfaces for real-time user feedback
- **Error History**: Maintains a history of errors for debugging and user support
- **Modular Error Handling**: Each module can raise errors that are caught and processed by the ErrorManager
- **Custom Error Types**: Allows for specific error handling based on module needs

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
