# Changelog

All notable changes to BenchFlow are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [v0.1.0] – 2026-05-22

### Added
- **Protocol Library** — create, import (PDF / DOCX / plain text), and organise
  wet-lab protocols with full step detail (reagents, equipment, timers, checklists)
- **Run Mode** — step-by-step protocol execution with countdown and hands-on timers,
  live status tracking, and automatic run recording
- **Schedule Calendar** — week / day calendar for planning experiments;
  compact per-session blocks with drag-to-move support
- **Timeline Editor** — right-panel day planner with editable blocks
  (Protocol Step, Break, Task, Note, Decision, Custom), skip/cancel with optional
  time removal, and cascading time recalculation
- **Lab Notebook** — persistent run history per protocol with actual timing,
  skipped steps, modifications, and notes
- **Flowchart View** — visual protocol flowchart for quick overview
- **macOS build system** — PyInstaller `.app` bundle + `.dmg` installer via
  `build_mac.sh` and `BenchFlow.spec`
- **Windows build system** — PyInstaller `.exe` + `.zip` distribution via
  `build_windows.bat` and `BenchFlow_windows.spec`
- **Unified build script** — `build.py` for cross-platform builds
- **GitHub Actions CI/CD** — automatic macOS and Windows builds on every push;
  automatic GitHub Release creation on version tags (`v*.*.*`)
