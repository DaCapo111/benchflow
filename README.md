# BenchFlow

**Interactive wet-lab workflow manager — protocol design, experiment scheduling, run tracking, and real-time lab organization.**

BenchFlow is a local-first macOS / Windows desktop app built with Python.  
No cloud. No account. All data stays on your machine.

> **Two versions available:**  
> `main` — stable release built with **CustomTkinter** (current distribution)  
> `qt-prototype` — in-development rebuild with **PySide6 / Qt6** (see below)

> **BenchFlow is distributed through [GitHub Releases](../../releases), not GitHub Packages.**  
> Future distribution options: Homebrew cask, pip package, signed installer.

---

## Download & Install

### 👉 [Latest release](../../releases/latest)

| Platform | Download | How to install |
|----------|----------|----------------|
| **macOS** | `BenchFlow-v0.1.0-macOS.dmg` | Open DMG → drag to Applications |
| **Windows** | `BenchFlow-v0.1.0-Windows.zip` | Unzip → run `BenchFlow.exe` |

Each release also includes `checksums.txt` (SHA-256) to verify your download.

### macOS

1. Download `BenchFlow-vX.X.X-macOS.dmg` from the [Releases page](../../releases).
2. Double-click the DMG to open it.
3. Drag **BenchFlow.app** into the **Applications** folder.
4. Open from Applications. On first launch macOS may show a security prompt:
   > **System Settings → Privacy & Security → "Open Anyway"**

### Windows

1. Download `BenchFlow-vX.X.X-Windows.zip` from the [Releases page](../../releases).
2. Unzip to any folder (e.g. `C:\Program Files\BenchFlow\`).
3. Run **BenchFlow.exe** inside the unzipped folder.
4. Windows SmartScreen may warn on first run since the app is unsigned:
   > Click **"More info" → "Run anyway"**

---

## Features

| | |
|---|---|
| 📋 **Protocol Library** | Create, import (PDF / DOCX / plain text), and organise protocols with step-by-step detail (reagents, equipment, timers, checklists) |
| 🗓 **Schedule Calendar** | Week / day calendar for planning experiments; drag-to-move blocks |
| ⏱ **Timeline Editor** | Right-panel day planner — add Breaks, Tasks, Notes, Decisions; skip steps; auto cascade time recalculation |
| ▶ **Run Mode** | Step-by-step protocol execution with countdown and hands-on timers |
| 📓 **Lab Notebook** | Persistent run history with actual timing, skipped steps, and notes |
| ⎇ **Flowchart View** | Visual protocol flowchart |

---

## PySide6 / Qt Version

> **Status: Merge candidate — ready to replace CTk on `main`.**

The Qt rewrite uses **PySide6 (Qt 6)** instead of CustomTkinter.  
All user data files are 100% compatible — switching between versions uses the same JSON files.

### Features

| Phase | Feature | Status |
|-------|---------|--------|
| 1–4.75 | App skeleton, Run Mode, Schedule, EventBus, AppState, Toast | ✅ |
| 5 | Protocol Library + Templates | ✅ |
| 6 | Protocol Editor (full CRUD, reagents, conditions, reorder) | ✅ |
| 7 | Lab Notebook (date-grouped, step table, edit notes) | ✅ |
| 8A | Flowchart (QGraphicsScene nodes, zoom/pan) | ✅ |
| 8B | Export (PDF/DOCX/JSON/MD) + Import (JSON/paste text) | ✅ |
| 9 | Settings, backup/restore, PyInstaller packaging | ✅ |
| Polish | App icon, settings persistence, CI Qt build, flowchart text | ✅ |

### Run the Qt version

```bash
# Install Qt dependencies
pip install -r requirements_qt.txt

# Optional: install export dependencies
pip install reportlab python-docx

# Run
python3 qt_app/main.py
```

User data and preferences are stored in:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/BenchFlow/` |
| Windows | `%APPDATA%\BenchFlow\` |
| Linux | `~/.local/share/BenchFlow/` |

Preferences (`autosave_interval_s`, `theme`, `session_recovery_enabled`) are persisted in `settings.json` in that folder.

### Build the Qt version

**macOS:**
```bash
chmod +x build_qt_mac.sh
./build_qt_mac.sh
# Output: dist/mac_qt/BenchFlow.app
#         releases/BenchFlow-Qt-v0.1.0-macOS.dmg
```

**Windows:**
```batch
build_qt_windows.bat
REM Output: dist\win_qt\BenchFlow_Qt\BenchFlow_Qt.exe
REM         releases\BenchFlow-Qt-v0.1.0-Windows.zip
```

### Qt dependencies

| Package | Required | Purpose |
|---------|----------|---------|
| `PySide6 >= 6.6` | **Yes** | UI framework |
| `reportlab >= 4.0` | No | PDF export |
| `python-docx >= 1.1` | No | Word export |
| `pyinstaller >= 6.0` | Build only | Packaging |

---

## Build from source (CTk version)

### Requirements

```
Python 3.10+
customtkinter >= 5.2.0
Pillow >= 10.0
PyInstaller >= 6.0
PyMuPDF          (optional — PDF import)
python-docx      (optional — DOCX import)
```

```bash
git clone https://github.com/DaCapo111/benchflow.git
cd benchflow
pip install -r requirements.txt
```

### Run without packaging

```bash
python3 app.py
```

### Build — macOS (.app + .dmg)

```bash
chmod +x build_mac.sh
./build_mac.sh

# Output:
#   dist/mac/BenchFlow.app
#   dist/mac/BenchFlow-v0.1.0-macOS.dmg
#   releases/BenchFlow-v0.1.0-macOS.dmg
```

### Build — Windows (.exe + .zip)

```batch
build_windows.bat

REM Output:
REM   dist\windows\BenchFlow\BenchFlow.exe
REM   dist\windows\BenchFlow-v0.1.0-Windows.zip
REM   releases\BenchFlow-v0.1.0-Windows.zip
```

### Unified build script

```bash
python3 build.py                 # current platform
python3 build.py --mac           # macOS only
python3 build.py --windows       # Windows only
python3 build.py --all           # both platforms
python3 build.py --no-dmg        # skip DMG creation
python3 build.py --no-clean      # skip clean step
python3 build.py --clean         # clean dist/ and build/ only
```

---

## Development workflow

```bash
# 1. Clone
git clone https://github.com/DaCapo111/benchflow.git
cd benchflow

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run directly (no build needed)
python3 app.py

# 4. Make changes to app.py

# 5. Test locally, then build
./build_mac.sh
```

---

## Release workflow

### Releasing a new version

```bash
# 1. Update the version number
echo "0.2.0" > VERSION

# 2. Document the changes
#    Edit CHANGELOG.md — add a new ## [v0.2.0] section

# 3. Commit
git add VERSION CHANGELOG.md
git commit -m "Release v0.2.0"

# 4. Tag the release
git tag v0.2.0

# 5. Push everything
git push origin main
git push origin v0.2.0
```

GitHub Actions will automatically:
1. Build macOS `.app` + `.dmg` on `macos-latest`
2. Build Windows `.exe` + `.zip` on `windows-latest`
3. Generate `checksums.txt`
4. Create a GitHub Release at `…/releases/tag/v0.2.0`
5. Attach `.dmg`, `.zip`, and `checksums.txt` as downloadable assets

### Artifacts on every push to main

Every push to `main` (without a tag) also triggers builds and stores them as  
GitHub Actions artifacts for 30 days — useful for testing before an official release.

---

## Project structure

```
app.py                    CTk main app (main branch — stable)
qt_app/                   PySide6 app (qt-prototype branch)
  main.py                 Qt entry point
  app.py                  BenchFlowApp(QMainWindow) — window + routing
  theme.py                Colors, Fonts, QSS
  services/               DataService, EventBus, AppState, export_service
  views/                  All Qt pages (library, editor, history, …)
  components/             Sidebar, widgets, toast
  dialogs/                New protocol, restore session dialogs

VERSION                   Current version number (e.g. 0.1.0)
CHANGELOG.md              Release history
requirements.txt          CTk dependencies
requirements_qt.txt       PySide6 dependencies

BenchFlow.spec            PyInstaller spec — CTk macOS bundle
BenchFlow_windows.spec    PyInstaller spec — CTk Windows exe
BenchFlow_Qt.spec         PyInstaller spec — Qt macOS bundle

build_mac.sh              One-click CTk macOS build
build_windows.bat         One-click CTk Windows build
build_qt_mac.sh           One-click Qt macOS build
build_qt_windows.bat      One-click Qt Windows build
build.py                  Unified cross-platform build script (CTk)

AppIcon.icns              macOS app icon
AppIcon.iconset/          Icon source images (all resolutions)
make_icon.py              Regenerate AppIcon.icns from source PNG

releases/                 Local staging for release-ready files
                          (.dmg / .zip copied here by build scripts)

docs/
  QT_FULL_MIGRATION.md    Full PySide6 migration plan & progress

.github/
  workflows/
    build.yml             GitHub Actions CI/CD
```

All user data is stored locally in:

```
~/Library/Application Support/BenchFlow/   (macOS)
%APPDATA%\BenchFlow\                        (Windows — planned)
```

---

## License

MIT — see [LICENSE](LICENSE).
