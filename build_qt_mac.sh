#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# BenchFlow Qt (PySide6) macOS build script
# Produces:  dist/mac_qt/BenchFlow.app
#            dist/mac_qt/BenchFlow-Qt-<version>-macOS.dmg
#
# Usage:
#   chmod +x build_qt_mac.sh
#   ./build_qt_mac.sh
#   ./build_qt_mac.sh --no-dmg     # skip DMG creation
#   ./build_qt_mac.sh --no-clean   # keep previous build/
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Config ───────────────────────────────────────────────────────────────────
VERSION=$(cat VERSION 2>/dev/null | tr -d '[:space:]' || echo "0.1.0")
APP_NAME="BenchFlow"
SPEC_FILE="BenchFlow_Qt.spec"
DIST_DIR="dist/mac_qt"
RELEASES_DIR="releases"
DMG_NAME="${APP_NAME}-Qt-v${VERSION}-macOS.dmg"

CREATE_DMG=true
DO_CLEAN=true
for arg in "$@"; do
  case $arg in
    --no-dmg)   CREATE_DMG=false ;;
    --no-clean) DO_CLEAN=false ;;
  esac
done

# ── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}▶ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠ $*${NC}"; }
error() { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }
ok()    { echo -e "${GREEN}✓ $*${NC}"; }

detach_benchflow_volumes() {
  for volume in /Volumes/"${APP_NAME} Qt"* /Volumes/"${APP_NAME}"*; do
    if [[ -d "$volume" ]]; then
      warn "Detaching existing volume: $volume"
      hdiutil detach "$volume" -force >/dev/null 2>&1 || true
    fi
  done
}

create_dmg() {
  local app_path="$1"
  local dmg_path="$2"
  local staging_dir

  staging_dir=$(mktemp -d)
  cleanup_dmg() {
    trap - RETURN
    detach_benchflow_volumes
    rm -rf "$staging_dir"
  }
  trap cleanup_dmg RETURN

  rm -f "$dmg_path"
  detach_benchflow_volumes

  cp -R "$app_path" "$staging_dir/"
  ln -sf /Applications "$staging_dir/Applications"
  xattr -cr "$staging_dir/${APP_NAME}.app" >/dev/null 2>&1 || true

  for attempt in 1 2 3; do
    info "hdiutil create attempt ${attempt}/3..."
    if (
      cd "$staging_dir"
      hdiutil create \
        -volname "${APP_NAME} Qt ${VERSION}" \
        -srcfolder "." \
        -ov -format UDZO \
        "$dmg_path" \
        >/dev/null
    ); then
      return 0
    fi

    rm -f "$dmg_path"
    detach_benchflow_volumes
    if [[ "$attempt" != "3" ]]; then
      sleep 5
    fi
  done

  return 1
}

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║   BenchFlow Qt macOS Build  v${VERSION}          ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# ── Platform check ───────────────────────────────────────────────────────────
[[ "$(uname)" == "Darwin" ]] || error "This script must run on macOS."

# ── Python ───────────────────────────────────────────────────────────────────
info "Checking Python..."
PYTHON=$(command -v python3 || error "python3 not found")
PY_VERSION=$("$PYTHON" --version 2>&1 | awk '{print $2}')
ok "Python $PY_VERSION ($PYTHON)"

# ── PyInstaller ───────────────────────────────────────────────────────────────
info "Checking PyInstaller..."
if ! "$PYTHON" -m PyInstaller --version &>/dev/null; then
  warn "PyInstaller not found – installing..."
  "$PYTHON" -m pip install pyinstaller --quiet
fi
PI_VERSION=$("$PYTHON" -m PyInstaller --version 2>&1)
ok "PyInstaller $PI_VERSION"

# ── PySide6 ───────────────────────────────────────────────────────────────────
info "Checking PySide6..."
if ! "$PYTHON" -c "import PySide6" &>/dev/null; then
  warn "PySide6 not found – installing..."
  "$PYTHON" -m pip install PySide6 --quiet
fi
ok "PySide6 found"

# ── Optional deps (export) ───────────────────────────────────────────────────
info "Checking optional export dependencies..."
for pkg in reportlab python-docx; do
  if "$PYTHON" -c "import ${pkg//-/_}" &>/dev/null; then
    ok "  $pkg ✓"
  else
    warn "  $pkg not installed (PDF/DOCX export will be unavailable)"
  fi
done

# ── Requirements ─────────────────────────────────────────────────────────────
if [[ -f requirements_qt.txt ]]; then
  info "Installing requirements_qt.txt..."
  "$PYTHON" -m pip install -r requirements_qt.txt --quiet
  ok "Requirements installed"
fi

# ── Clean ─────────────────────────────────────────────────────────────────────
if $DO_CLEAN; then
  info "Cleaning old artifacts..."
  rm -rf build/ "$DIST_DIR"
  ok "Cleaned"
fi

mkdir -p "$DIST_DIR" "$RELEASES_DIR"

# ── Build .app ────────────────────────────────────────────────────────────────
info "Building ${APP_NAME}.app with PySide6..."
"$PYTHON" -m PyInstaller --noconfirm \
  --distpath "$DIST_DIR" \
  --workpath build \
  "$SPEC_FILE"

APP_PATH="${DIST_DIR}/${APP_NAME}.app"
[[ -d "$APP_PATH" ]] || error "Build failed – ${APP_NAME}.app not found."
APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
ok "${APP_NAME}.app  (${APP_SIZE})"

# ── Create DMG ────────────────────────────────────────────────────────────────
if $CREATE_DMG; then
  info "Creating ${DMG_NAME}..."
  DMG_PATH="${SCRIPT_DIR}/${DIST_DIR}/${DMG_NAME}"

  if create_dmg "$APP_PATH" "$DMG_PATH" && [[ -f "$DMG_PATH" ]]; then
    DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
    ok "${DMG_NAME}  (${DMG_SIZE})"
    cp "$DMG_PATH" "${RELEASES_DIR}/${DMG_NAME}"
    ok "Copied to releases/${DMG_NAME}"
  else
    error "DMG creation failed."
  fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  BenchFlow Qt build complete!"
echo ""
echo "  Output:"
ls -lh "$DIST_DIR" | tail -n +2
echo ""
echo "  To run:"
echo "    open ${DIST_DIR}/${APP_NAME}.app"
echo ""
echo "  Or from source:"
echo "    python3 qt_app/main.py"
echo "══════════════════════════════════════════════"
