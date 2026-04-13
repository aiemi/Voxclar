#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Voxclar — Unified Build Script
# ─────────────────────────────────────────────────────────────────
# Usage:
#   ./scripts/build.sh              # build for current arch (arm64)
#   ./scripts/build.sh --arch x64   # build for Intel
#   ./scripts/build.sh --no-protect # skip code protection
#   ./scripts/build.sh --clean      # clean all build artifacts first
#
# Environment:
#   VOXCLAR_PROTECT=0  — same as --no-protect
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DESKTOP_DIR="$PROJECT_ROOT/packages/desktop"
ENGINE_DIR="$PROJECT_ROOT/packages/local-engine"
BUILDS_DIR="$PROJECT_ROOT/builds"

# ── Defaults ────────────────────────────────────────────────────
ARCH="$(uname -m)"                       # arm64 or x86_64
PROTECT="${VOXCLAR_PROTECT:-1}"          # 1=obfuscate, 0=skip
CLEAN=0

# ── Parse args ──────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --arch)      ARCH="$2"; shift 2 ;;
    --no-protect) PROTECT=0; shift ;;
    --clean)     CLEAN=1; shift ;;
    *)           echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# Normalize arch name for electron-builder
if [[ "$ARCH" == "x86_64" || "$ARCH" == "x64" || "$ARCH" == "intel" ]]; then
  EB_ARCH="x64"
  ARCH_LABEL="x64"
elif [[ "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
  EB_ARCH="arm64"
  ARCH_LABEL="arm64"
else
  echo "Unsupported arch: $ARCH"; exit 1
fi

# Detect version from package.json productName
PRODUCT_NAME=$(node -e "console.log(require('$DESKTOP_DIR/package.json').build.productName)")
IS_LIFETIME=0
[[ "$PRODUCT_NAME" == *"Lifetime"* ]] && IS_LIFETIME=1

echo "╔═══════════════════════════════════════════════════════╗"
echo "║  Voxclar Build — $PRODUCT_NAME"
echo "║  Arch: $ARCH_LABEL  |  Protect: $PROTECT  |  Clean: $CLEAN"
echo "╚═══════════════════════════════════════════════════════╝"

cd "$PROJECT_ROOT"

# ── Step 0: Clean ───────────────────────────────────────────────
if [[ $CLEAN -eq 1 ]]; then
  echo "🧹 Cleaning..."
  rm -rf "$ENGINE_DIR/build" "$ENGINE_DIR/dist" "$ENGINE_DIR/__pyarmor_obf"
  rm -rf "$DESKTOP_DIR/dist" "$DESKTOP_DIR/dist-electron" "$DESKTOP_DIR/app-dist"
  rm -rf "$BUILDS_DIR"
fi

# ── Step 1: Swift Audio Helper (macOS only) ─────────────────────
SWIFT_HELPER="$ENGINE_DIR/imeet_audio_capture"
if [[ "$(uname)" == "Darwin" && ! -f "$SWIFT_HELPER" ]]; then
  echo "🔨 Compiling Swift audio capture helper..."
  python3 -c "
import sys; sys.path.insert(0, '$ENGINE_DIR')
from src.audio.macos_capture import _SWIFT_CAPTURE_SOURCE
with open('$ENGINE_DIR/imeet_audio_capture.swift', 'w') as f:
    f.write(_SWIFT_CAPTURE_SOURCE)
"
  swiftc -O \
    -framework ScreenCaptureKit \
    -framework CoreMedia \
    -framework AVFoundation \
    "$ENGINE_DIR/imeet_audio_capture.swift" -o "$SWIFT_HELPER"
  echo "   ✓ Swift helper compiled ($(du -h "$SWIFT_HELPER" | awk '{print $1}'))"
elif [[ -f "$SWIFT_HELPER" ]]; then
  echo "✓ Swift helper already exists"
fi

# ── Step 2: Python Code Protection (PyArmor) ───────────────────
PYINSTALLER_SRC="$ENGINE_DIR"
if [[ $PROTECT -eq 1 ]]; then
  echo "🔒 Obfuscating Python code with PyArmor..."
  OBF_DIR="$ENGINE_DIR/__pyarmor_obf"
  rm -rf "$OBF_DIR"
  mkdir -p "$OBF_DIR"

  # Copy source for obfuscation
  cp -R "$ENGINE_DIR/src" "$OBF_DIR/src"
  [[ -f "$ENGINE_DIR/run_engine.py" ]] && cp "$ENGINE_DIR/run_engine.py" "$OBF_DIR/"

  # Obfuscate
  pyarmor gen \
    --output "$OBF_DIR" \
    --recursive \
    "$OBF_DIR/src/" 2>&1 | tail -5

  PYINSTALLER_SRC="$OBF_DIR"
  echo "   ✓ Python obfuscated"
else
  echo "⏭️  Skipping Python protection"
fi

# ── Step 3: PyInstaller — Build Engine ──────────────────────────
echo "📦 Building Python engine with PyInstaller..."
cd "$ENGINE_DIR"
rm -rf build/ dist/
pyinstaller voxclar-engine.spec --clean 2>&1 | tail -5
echo "   ✓ Engine built ($(du -sh dist/voxclar-engine/ | awk '{print $1}'))"

# ── Step 4: Copy Engine → Desktop ──────────────────────────────
echo "📋 Copying engine to desktop build..."
rm -rf "$DESKTOP_DIR/build/engine/"*
cp -pR dist/voxclar-engine/* "$DESKTOP_DIR/build/engine/"
echo "   ✓ Engine copied"

# ── Step 5: Build Electron + Web ────────────────────────────────
echo "🌐 Building Electron + Web..."
cd "$DESKTOP_DIR"
npm run build:electron 2>&1 | tail -2
npm run build:web 2>&1 | tail -2
echo "   ✓ Web bundle ready"

# ── Step 6: JS Code Protection ──────────────────────────────────
if [[ $PROTECT -eq 1 ]]; then
  echo "🔒 Obfuscating JavaScript..."
  # Find the main JS bundle(s) in app-dist/assets/
  for jsfile in "$DESKTOP_DIR/app-dist/assets/"*.js; do
    [[ -f "$jsfile" ]] || continue
    SIZE_BEFORE=$(wc -c < "$jsfile")
    npx javascript-obfuscator "$jsfile" \
      --output "$jsfile" \
      --compact true \
      --control-flow-flattening true \
      --control-flow-flattening-threshold 0.3 \
      --dead-code-injection false \
      --string-array true \
      --string-array-threshold 0.5 \
      --string-array-encoding base64 \
      --rename-globals false \
      --self-defending false \
      --unicode-escape-sequence false 2>/dev/null
    SIZE_AFTER=$(wc -c < "$jsfile")
    echo "   ✓ $(basename "$jsfile"): ${SIZE_BEFORE}B → ${SIZE_AFTER}B"
  done
else
  echo "⏭️  Skipping JS protection"
fi

# ── Step 7: Package with electron-builder ───────────────────────
echo "📱 Packaging app with electron-builder..."
rm -rf dist/
npx electron-builder \
  --mac \
  --$EB_ARCH \
  --config.mac.identity=null \
  --config.mac.notarize=false \
  2>&1 | tail -5
echo "   ✓ Packaged"

# ── Step 8: Copy to Builds ─────────────────────────────────────
echo "📁 Copying to builds/..."
mkdir -p "$BUILDS_DIR"

APP_DIR=$(find dist/ -name "*.app" -maxdepth 2 -type d | head -1)
DMG_FILE=$(find dist/ -name "*.dmg" -maxdepth 1 -type f | head -1)

if [[ -n "$APP_DIR" ]]; then
  APP_NAME="$(basename "$APP_DIR")"
  rm -rf "$BUILDS_DIR/$APP_NAME"
  ditto "$APP_DIR" "$BUILDS_DIR/$APP_NAME"
  APP_SIZE=$(du -sh "$BUILDS_DIR/$APP_NAME" | awk '{print $1}')
  echo "   ✓ $APP_NAME ($APP_SIZE)"
fi

if [[ -n "$DMG_FILE" ]]; then
  cp "$DMG_FILE" "$BUILDS_DIR/"
  DMG_SIZE=$(du -h "$DMG_FILE" | awk '{print $1}')
  echo "   ✓ $(basename "$DMG_FILE") ($DMG_SIZE)"
fi

# ── Step 9: Install to /Applications (cloud only) ──────────────
if [[ $IS_LIFETIME -eq 0 && -n "$APP_DIR" ]]; then
  rm -rf "/Applications/$APP_NAME"
  ditto "$APP_DIR" "/Applications/$APP_NAME"
  echo "   ✓ Installed to /Applications/$APP_NAME"
fi

# ── Cleanup ─────────────────────────────────────────────────────
rm -rf "$ENGINE_DIR/__pyarmor_obf"

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║  ✅ Build complete!                                    ║"
echo "║  Output: $BUILDS_DIR/"
echo "╚═══════════════════════════════════════════════════════╝"
