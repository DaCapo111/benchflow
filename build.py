#!/usr/bin/env python3
"""
BenchFlow unified build script.

Usage:
  python3 build.py                # build for current platform
  python3 build.py --mac          # macOS only  (must be on macOS)
  python3 build.py --windows      # Windows only (must be on Windows)
  python3 build.py --all          # all platforms (skips unsupported)
  python3 build.py --no-clean     # skip cleaning previous artifacts
  python3 build.py --no-dmg       # skip DMG creation on macOS
  python3 build.py --version 1.2  # override version string
  python3 build.py --clean        # clean only, do not build
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.resolve()
VERSION = "1.0.0"


# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd: list, **kwargs) -> None:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    subprocess.run([str(c) for c in cmd], check=True, cwd=ROOT, **kwargs)


def header(text: str) -> None:
    bar = "═" * (len(text) + 4)
    print(f"\n╔{bar}╗\n║  {text}  ║\n╚{bar}╝")


def step(n: int, total: int, text: str) -> None:
    print(f"\n[{n}/{total}] {text}")


def ok(text: str)   -> None: print(f"  ✓ {text}")
def warn(text: str) -> None: print(f"  ⚠ {text}")
def err(text: str)  -> None: print(f"  ✗ {text}", file=sys.stderr)


def human_size(path: Path) -> str:
    if path.is_dir():
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    else:
        total = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if total < 1024:
            return f"{total:.0f} {unit}"
        total /= 1024
    return f"{total:.1f} GB"


# ── Icon conversion ───────────────────────────────────────────────────────────
def ensure_ico() -> Path | None:
    """Convert AppIcon.icns → AppIcon.ico (Windows format) using Pillow."""
    ico_path = ROOT / "AppIcon.ico"
    if ico_path.exists():
        return ico_path
    icns_path = ROOT / "AppIcon.icns"
    if not icns_path.exists():
        warn("AppIcon.icns not found – building without icon.")
        return None
    try:
        from PIL import Image
        img = Image.open(icns_path)
        img.save(ico_path, format="ICO",
                 sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        ok(f"AppIcon.ico created ({human_size(ico_path)})")
        return ico_path
    except Exception as e:
        warn(f"Icon conversion failed ({e}) – building without icon.")
        return None


# ── Clean ─────────────────────────────────────────────────────────────────────
def clean(targets: list[Path] | None = None) -> None:
    if targets is None:
        targets = [ROOT / "build", ROOT / "dist" / "mac",
                   ROOT / "dist" / "windows"]
    for d in targets:
        if d.exists():
            shutil.rmtree(d)
            ok(f"Removed {d.relative_to(ROOT)}")
        else:
            print(f"  – {d.relative_to(ROOT)} (already clean)")


# ── Requirements ──────────────────────────────────────────────────────────────
def install_requirements() -> None:
    req = ROOT / "requirements.txt"
    if req.exists():
        run([sys.executable, "-m", "pip", "install", "-r", req, "-q"])
        ok("Requirements installed")
    # Ensure PyInstaller is available
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError:
        run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
        ok("PyInstaller installed")


# ── macOS build ───────────────────────────────────────────────────────────────
def build_mac(version: str, create_dmg: bool = True) -> bool:
    if platform.system() != "Darwin":
        warn("Skipping macOS build (not on macOS).")
        return False

    header(f"BenchFlow macOS build  v{version}")

    dist_path = ROOT / "dist" / "mac"
    dist_path.mkdir(parents=True, exist_ok=True)
    releases  = ROOT / "releases"
    releases.mkdir(exist_ok=True)

    step(1, 3, "Running PyInstaller…")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm",
         "--distpath", dist_path,
         "--workpath", ROOT / "build",
         ROOT / "BenchFlow.spec"])

    app_path = dist_path / "BenchFlow.app"
    if not app_path.exists():
        err("BenchFlow.app not found after build.")
        return False
    ok(f"BenchFlow.app  ({human_size(app_path)})")

    if not create_dmg:
        return True

    step(2, 3, "Creating DMG…")
    dmg_name = f"BenchFlow-{version}-mac.dmg"
    dmg_path = dist_path / dmg_name
    try:
        tmp = Path(tempfile.mkdtemp())
        shutil.copytree(app_path, tmp / "BenchFlow.app")
        (tmp / "Applications").symlink_to("/Applications")
        run(["hdiutil", "create",
             "-volname", "BenchFlow",
             "-srcfolder", tmp,
             "-ov", "-format", "UDZO",
             dmg_path],
            stdout=subprocess.DEVNULL)
        shutil.rmtree(tmp)
        if dmg_path.exists():
            ok(f"{dmg_name}  ({human_size(dmg_path)})")
            shutil.copy(dmg_path, releases / dmg_name)
            ok(f"Copied → releases/{dmg_name}")
    except Exception as e:
        warn(f"DMG creation failed: {e}\n  .app is still available.")

    step(3, 3, "Summary")
    for f in sorted(dist_path.iterdir()):
        print(f"  {f.name:<40} {human_size(f)}")
    return True


# ── Windows build ─────────────────────────────────────────────────────────────
def build_windows(version: str) -> bool:
    if platform.system() != "Windows":
        warn("Skipping Windows build (not on Windows).")
        return False

    header(f"BenchFlow Windows build  v{version}")

    ensure_ico()

    dist_path = ROOT / "dist" / "windows"
    dist_path.mkdir(parents=True, exist_ok=True)
    releases  = ROOT / "releases"
    releases.mkdir(exist_ok=True)

    step(1, 3, "Running PyInstaller…")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm",
         "--distpath", dist_path,
         "--workpath", ROOT / "build",
         ROOT / "BenchFlow_windows.spec"])

    exe_path = dist_path / "BenchFlow" / "BenchFlow.exe"
    if not exe_path.exists():
        err("BenchFlow.exe not found after build.")
        return False
    ok(f"BenchFlow.exe  ({human_size(exe_path)})")

    step(2, 3, "Creating ZIP for distribution…")
    zip_name = f"BenchFlow-{version}-windows"
    zip_path = dist_path / zip_name
    shutil.make_archive(str(zip_path), "zip", dist_path / "BenchFlow")
    final_zip = Path(str(zip_path) + ".zip")
    if final_zip.exists():
        ok(f"{final_zip.name}  ({human_size(final_zip)})")
        shutil.copy(final_zip, releases / final_zip.name)
        ok(f"Copied → releases/{final_zip.name}")

    step(3, 3, "Summary")
    for f in sorted(dist_path.iterdir()):
        print(f"  {f.name:<40} {human_size(f)}")
    return True


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="BenchFlow build script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--mac",       action="store_true", help="Build macOS only")
    parser.add_argument("--windows",   action="store_true", help="Build Windows only")
    parser.add_argument("--all",       action="store_true", help="Build all platforms")
    parser.add_argument("--clean",     action="store_true", help="Clean only, no build")
    parser.add_argument("--no-clean",  action="store_true", help="Skip clean step")
    parser.add_argument("--no-dmg",    action="store_true", help="Skip DMG creation")
    parser.add_argument("--version",   default=VERSION,     help=f"Version string (default {VERSION})")
    args = parser.parse_args()

    os.chdir(ROOT)
    ver = args.version

    if args.clean:
        clean(); return

    do_mac     = args.mac     or args.all or (not args.windows)
    do_windows = args.windows or args.all

    if not args.no_clean:
        print("\nCleaning previous artifacts…")
        clean()

    install_requirements()

    success = []
    if do_mac:
        if build_mac(ver, create_dmg=not args.no_dmg):
            success.append("macOS")
    if do_windows:
        if build_windows(ver):
            success.append("Windows")

    print(f"\n{'═'*44}")
    if success:
        print(f"  Build complete: {', '.join(success)}")
        print(f"  Artifacts in:   dist/  and  releases/")
    else:
        print("  No builds completed for this platform.")
    print(f"{'═'*44}\n")


if __name__ == "__main__":
    main()
