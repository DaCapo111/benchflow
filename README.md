# BenchFlow

**Interactive wet-lab workflow manager for protocol design, experiment scheduling, run tracking, and real-time lab organization.**

BenchFlow is a local-first macOS desktop app built with Python and CustomTkinter. No cloud, no account required — all data lives on your machine.

---

## Features

- **Protocol Library** — Create, import (PDF/DOCX/text), and organise wet-lab protocols with step-by-step detail (reagents, timing, equipment, checklists).
- **Schedule Calendar** — Place experiments on a week/day calendar. The right-panel Timeline Editor lets you edit every block in the day's plan without touching the macro calendar view.
- **Timeline Editor** — Add/edit/delete/reorder blocks (Protocol Step, Break, Task, Note, Decision, Custom). Skip or cancel steps with optional time removal. Full time recalculation cascades automatically.
- **Run Mode** — Step-by-step execution with built-in timers (countdown / hands-on), live status tracking, and completion recording.
- **Lab Notebook** — Persisted run history per protocol with actual timing, skipped steps, and notes.
- **Flowchart View** — Visual protocol flowchart for quick overview.

---

## Requirements

```
Python 3.10+
customtkinter
PyMuPDF (optional, for PDF import)
python-docx (optional, for DOCX import)
PyInstaller (to build the .app bundle)
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Running from source

```bash
python3 app.py
```

---

## Building the macOS app

```bash
python3 -m PyInstaller --noconfirm BenchFlow.spec
# Output: dist/BenchFlow.app
```

---

## Project structure

```
app.py              # Single-file application (all UI + logic)
BenchFlow.spec      # PyInstaller build spec
requirements.txt    # Python dependencies
make_icon.py        # Script to generate AppIcon.icns
AppIcon.icns        # macOS app icon
AppIcon.iconset/    # Icon source images
```

All user data (protocols, runs, schedule) is stored in:

```
~/Library/Application Support/BenchFlow/
```

---

## License

MIT — see [LICENSE](LICENSE).
