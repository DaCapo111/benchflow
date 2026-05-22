# BenchFlow

**Interactive wet-lab workflow manager — protocol design, experiment scheduling, run tracking, and real-time lab organization.**

BenchFlow is a local-first macOS/Windows desktop app built with Python + CustomTkinter.  
No cloud. No account. All data stays on your machine.

---

## Download & Install

### Latest release

👉 **[Releases page](../../releases/latest)**

| Platform | File | Instructions |
|----------|------|-------------|
| **macOS** | `BenchFlow-x.x.x-mac.dmg` | Open DMG → drag to Applications |
| **Windows** | `BenchFlow-x.x.x-windows.zip` | Unzip → run `BenchFlow.exe` |

### macOS install

1. Download `BenchFlow-x.x.x-mac.dmg` from the Releases page.
2. Double-click the DMG to open it.
3. Drag **BenchFlow.app** into the **Applications** folder.
4. Open from Applications. If macOS shows a security warning:
   - **System Settings → Privacy & Security → Open Anyway**

### Windows install

1. Download `BenchFlow-x.x.x-windows.zip` from the Releases page.
2. Unzip the archive to any folder (e.g. `C:\Program Files\BenchFlow\`).
3. Run `BenchFlow.exe` inside the unzipped folder.
4. Optional: right-click `BenchFlow.exe` → *Create shortcut* → move to Desktop.

> **Note:** Windows may show a SmartScreen warning on first run since the app
> is not code-signed. Click "More info" → "Run anyway".

---

## Features

- **Protocol Library** — Create, import (PDF / DOCX / plain text), and organize wet-lab protocols with step-by-step detail (reagents, timing, equipment, checklists).
- **Schedule Calendar** — Place experiments on a week / day calendar grid.
- **Timeline Editor** — Edit the day's plan in the right panel: add breaks, tasks, notes, decisions; skip steps with optional time removal; cascade time recalculation.
- **Run Mode** — Step-by-step execution with built-in timers (countdown / hands-on), live status tracking, and completion recording.
- **Lab Notebook** — Persisted run history per protocol with actual timing, skipped steps, and notes.
- **Flowchart View** — Visual protocol flowchart for quick overview.

---

## Building from source

### Requirements

```
Python 3.10+
customtkinter >= 5.2.0
Pillow >= 10.0
PyMuPDF        (optional — PDF import)
python-docx    (optional — DOCX import)
PyInstaller >= 6.0
```

```bash
pip install -r requirements.txt
```

### Run without building

```bash
python3 app.py
```

### macOS — build .app + .dmg

```bash
chmod +x build_mac.sh
./build_mac.sh
# Output: dist/mac/BenchFlow.app
#         dist/mac/BenchFlow-1.0.0-mac.dmg
#         releases/BenchFlow-1.0.0-mac.dmg
```

### Windows — build .exe + .zip

```batch
build_windows.bat
# Output: dist\windows\BenchFlow\BenchFlow.exe
#         dist\windows\BenchFlow-1.0.0-windows.zip
#         releases\BenchFlow-1.0.0-windows.zip
```

### Unified build script (cross-platform)

```bash
python3 build.py            # current platform
python3 build.py --mac      # macOS only
python3 build.py --windows  # Windows only
python3 build.py --all      # both (runs unsupported targets gracefully)
python3 build.py --no-dmg   # skip DMG
python3 build.py --clean    # clean dist/ and build/ only
```

---

## Publishing a release

### Automatic (recommended)

Push a version tag — GitHub Actions builds both platforms and creates the release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The `build.yml` workflow will:
1. Build `BenchFlow.app` + `.dmg` on `macos-latest`
2. Build `BenchFlow.exe` + `.zip` on `windows-latest`
3. Create a GitHub Release and attach both files as assets

### Manual

1. Build locally with `build_mac.sh` / `build_windows.bat`
2. Files land in `releases/`
3. Go to **GitHub → Releases → Draft a new release**
4. Attach `.dmg` and `.zip` from `releases/`

---

## Project structure

```
app.py                    # Single-file application (all UI + logic)
BenchFlow.spec            # PyInstaller spec — macOS
BenchFlow_windows.spec    # PyInstaller spec — Windows
build_mac.sh              # One-click macOS build
build_windows.bat         # One-click Windows build
build.py                  # Unified Python build script
requirements.txt          # Python dependencies
make_icon.py              # Generates AppIcon.icns from source PNG
AppIcon.icns              # macOS app icon
AppIcon.iconset/          # Icon source images (all sizes)
releases/                 # Staging folder for release-ready files
.github/workflows/
  build.yml               # GitHub Actions CI/CD
```

All user data is stored locally in:

```
~/Library/Application Support/BenchFlow/   (macOS)
%APPDATA%\BenchFlow\                        (Windows)
```

---

## License

MIT — see [LICENSE](LICENSE).
