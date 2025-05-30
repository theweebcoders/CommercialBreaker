# CommercialBreaker & Toonami Tools

Welcome to the comprehensive documentation for CommercialBreaker & Toonami Tools - the ultimate solution for recreating the authentic Toonami experience with your anime collection.

## What is this project?

CommercialBreaker & Toonami Tools automate a continuous Toonami marathon by intelligently inserting commercial breaks into anime episodes and organizing them with authentic Toonami bumps. The tools slice up your anime, add nostalgic commercial breaks, and create seamless marathon experiences that feel just like those late-night Toonami sessions.

## Key Features

- **CommercialBreaker**: Intelligently detects and creates commercial break points in anime episodes
- **Cutless Mode**: Preserve original files while adding virtual commercial breaks
- **Toonami Tools**: Generate custom lineups with authentic bump integration
- **Multiple Interfaces**: GUI (TOM), Web UI (Absolution), and CLI (Clydes)
- **Platform Support**: Works with DizqueTV and Tunarr for channel creation
- **Plex Integration**: Seamless integration with your existing Plex library

## Quick Start

1. **[Installation Guide](Installation-Guide.md)** - Get up and running quickly
2. **[User Guides](User-Guides.md)** - Choose your interface and start creating
3. **[Configuration](Configuration-Reference.md)** - Customize your setup

## Documentation Sections

### User Documentation
- **[Installation Guide](Installation-Guide.md)** - Step-by-step setup instructions
- **[User Guides](User-Guides.md)** - Interface-specific guides
- **[Cutless Mode](Cutless.md)** - How to use virtual cuts instead of physical files
- **[File Naming Conventions](File-Naming-Conventions.md)** - Proper naming schemes
- **[Troubleshooting](Troubleshooting.md)** - Common issues and solutions
- **[FAQ](FAQ.md)** - Frequently asked questions

### Technical Documentation
- **[Architecture Overview](Architecture-Overview.md)** - System design and components
- **[API Reference](API-Reference.md)** - Technical implementation details
- **[Component Documentation](Component-Documentation.md)** - Individual tool descriptions
- **[Developer Guide](Developer-Guide.md)** - Contributing and development info

### Reference Materials
- **[Configuration Reference](Configuration-Reference.md)** - All configuration options
- **[Docker Setup](Docker-Setup.md)** - Container deployment
- **[Platform Integration](Platform-Integration.md)** - DizqueTV and Tunarr setup

## Project Structure

The project is organized into several key directories, each serving a specific purpose:

```
CommercialBreaker/
├── main.py                 # Entry point - selects which interface to run
├── API/                    # Core application logic and orchestration
├── GUI/                    # Graphical User Interfaces (TOM, Absolution)
├── CLI/                    # Command-Line Interfaces (clydes)
├── ComBreak/               # Commercial detection and processing tools
├── ToonamiTools/           # All the tools for Toonami channel creation: Plex integration, media/bump handling, lineup scheduling, and platform deployment
└── ExtraTools/             # Case Use tools and utilities
```

## Getting Help

- **[FAQ](FAQ.md)** - Check common questions first
- **[Troubleshooting](Troubleshooting.md)** - Solve specific issues
- **Discord**: [Join our community](https://discord.gg/S7NcUdhKRD)
- **GitHub Issues**: Report bugs and request features
- **ChatGPT**: Give all these documents and a link to the repo to ChatGPT for assistance

## Contributing

See our **[Developer Guide](Developer-Guide.md)** for information on contributing to the project.

---

*"Until next time, Space Cowboy!"*
