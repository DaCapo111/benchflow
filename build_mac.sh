#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# BenchFlow macOS build script
# Produces:  dist/mac/BenchFlow.app
#            dist/mac/BenchFlow-<version>-mac.dmg
#
# Usage:
#   chmod +x build_mac.sh
#   ./build_mac.sh
#   ./build_mac.sh --no-dmg     # skip DMG creation
#   ./build_mac.sh --no-clean   # keep previous build/
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Config ───────────────────────────────────────────────────────────────────
VERSION="1.0.0"
APP_NAME="BenchFlow"
SPEC_FILE="BenchFlow.spec"
DIST_DIR="dist/mac"
RELEASES_DIR="releases"
DMG_NAME="${APP_NAME}-${VERSION}-mac.dmg"

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

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   BenchFlow macOS Build  v${VERSION}       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Platform check ───────────────────────────────────────────────────────────
[[ "$(uname)" == "Darwin" ]] || error "This script must run on macOS."

# ── Python check ─────────────────────────────────────────────────────────────
info "Checking Python..."
PYTHON=$(command -v python3 || command -v python || error "python3 not found")
PY_VERSION=$("$PYTHON" --version 2>&1 | awk '{print $2}')
ok "Python $PY_VERSION ($PYTHON)"

# ── PyInstaller check ─────────────────────────────────────────────────────────
info "Checking PyInstaller..."
if ! "$PYTHON" -m PyInstaller --version &>/dev/null; then
  warn "PyInstaller not found – installing..."
  "$PYTHON" -m pip install pyinstaller --quiet
fi
PI_VERSION=$("$PYTHON" -m PyInstaller --version 2>&1)
ok "PyInstaller $PI_VERSION"

# ── Requirements ─────────────────────────────────────────────────────────────
info "Installing requirements..."
"$PYTHON" -m pip install -r requirements.txt --quiet
ok "Requirements installed"

# ── Clean ─────────────────────────────────────────────────────────────────────
if $DO_CLEAN; then
  info "Cleaning old artifacts..."
  rm -rf build/ "$DIST_DIR"
  ok "Cleaned"
fi

mkdir -p "$DIST_DIR" "$RELEASES_DIR"

# ── Build .app ────────────────────────────────────────────────────────────────
info "Building ${APP_NAME}.app..."
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
  DMG_PATH="${DIST_DIR}/${DMG_NAME}"

  TMP_DIR=$(mktemp -d)
  cp -R "$APP_PATH" "${TMP_DIR}/"
  ln -sf /Applications "${TMP_DIR}/Applications"

  hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$TMP_DIR" \
    -ov -format UDZO \
    "$DMG_PATH" \
    >/dev/null

  rm -rf "$TMP_DIR"

  if [[ -f "$DMG_PATH" ]]; then
    DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
    ok "${DMG_NAME}  (${DMG_SIZE})"
    # Copy to releases/ for easy GitHub Release upload
    cp "$DMG_PATH" "${RELEASES_DIR}/${DMG_NAME}"
    ok "Copied to releases/${DMG_NAME}"
  else
    warn "DMG creation failed – .app still available."
  fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo "  Build complete!"
echo ""
echo "  Output:"
ls -lh "$DIST_DIR" | tail -n +2
echo ""
echo "  To install:"
echo "    open ${DMG_PATH:-$APP_PATH}"
echo "══════════════════════════════════════════"
